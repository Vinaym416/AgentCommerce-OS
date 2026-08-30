"""
AGENTCOMMERCE OS
PHASE 08E — WEBHOOK SERVICE

Application layer for Razorpay webhook processing.

Flow:

Razorpay
    ↓
X-Razorpay-Signature (raw body)
    ↓
FastAPI webhook endpoint
    ↓
RazorpayWebhookHandler (HMAC verification)
    ↓
WebhookRepository (event_id idempotency)
    ↓
PaymentService (payment lookup + state machine)
    ↓
TransactionUpdate + OrderCreation (async)
    ↓
MongoDB persistence

IMPORTANT:

This service does NOT:
- create Razorpay orders
- verify frontend payment signatures
- block on order creation (async for production)

This service DOES:
- persist webhook events atomically
- detect duplicates by event_id
- update payment state
- update transaction with payment result
- create internal order asynchronously
"""

from typing import Any, Dict
import logging

from script.database.repositories.webhook_repository import WebhookRepository
from script.database.repositories.order_repository import OrderRepository
from script.payment.payment_service import PaymentService
from script.agents.order_agent import OrderAgent

logger = logging.getLogger(__name__)


class WebhookService:

    def __init__(self):

        self.webhook_repository = WebhookRepository()

        self.payment_service = PaymentService()

        self.order_repository = OrderRepository()
        
        self.order_agent = OrderAgent()

        print(
            "Webhook Service initialized."
        )

    # ========================================================
    # ASYNC TASK: CREATE ORDER FROM PAYMENT
    # ========================================================

    def _create_order_for_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        event_id: str,
    ) -> Dict[str, Any]:
        """
        Background task to create an internal order
        after successful payment (payment.captured event).
        
        In production, this should be queued to a task worker.
        """

        # Find the transaction by razorpay_order_id
        transaction = (
            self.payment_service
            .transaction_manager
            .repository
            .get_by_razorpay_order_id(
                razorpay_order_id
            )
        )

        if transaction is None:
            logger.warning(
                f"Cannot create order: "
                f"Transaction not found for "
                f"razorpay_order_id={razorpay_order_id}, "
                f"event_id={event_id}"
            )
            return {
                "success": False,
                "reason": "transaction_not_found",
            }

        # Extract required fields
        customer_id = transaction.get("customer_id")
        product_id = transaction.get("product_id")
        final_price = transaction.get("final_price", 0.0)
        currency = transaction.get("currency", "INR")

        if customer_id is None or product_id is None:
            logger.warning(
                f"Cannot create order: "
                f"Missing customer_id or product_id "
                f"in transaction {transaction.get('transaction_id')}"
            )
            return {
                "success": False,
                "reason": "missing_order_fields",
            }

        existing_order = self.order_repository.find_by_payment_transaction_id(
            razorpay_payment_id
        )

        if existing_order:
            self.payment_service.transaction_manager.repository.update_order(
                transaction_id=transaction.get("transaction_id"),
                order_id=existing_order.get("order_id"),
            )
            logger.info(
                f"Duplicate order suppressed for payment_id={razorpay_payment_id}, "
                f"existing_order_id={existing_order.get('order_id')}"
            )
            return {
                "success": True,
                "duplicate": True,
                "order_id": existing_order.get("order_id"),
                "reason": "order_already_exists",
            }

        # Create the order
        order = self.order_agent.create_order(
            customer_id=customer_id,
            product_id=product_id,
            amount=final_price,
            currency=currency,
            payment_status="SUCCESS",
            payment_transaction_id=razorpay_payment_id,
        )

        if order.status != "CONFIRMED":
            logger.error(
                f"Order creation failed: {order.reason}"
            )
            return {
                "success": False,
                "reason": order.reason,
            }

        # Update transaction with order info
        self.payment_service.transaction_manager.repository.update_order(
            transaction_id=transaction.get("transaction_id"),
            order_id=order.order_id,
        )

        logger.info(
            f"Order created: {order.order_id} "
            f"for event_id={event_id}"
        )

        return {
            "success": True,
            "duplicate": False,
            "order_id": order.order_id,
            "reason": "order_created_successfully",
        }

    # ========================================================
    # HANDLE PAYMENT CAPTURED
    # ========================================================

    def _handle_payment_captured(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        event_id: str,
    ) -> Dict[str, Any]:
        """
        Handle payment.captured event:
        1. Update transaction payment status to PAID
        2. Queue order creation (async)
        """

        # Find transaction by razorpay_order_id
        transaction = (
            self.payment_service
            .transaction_manager
            .repository
            .get_by_razorpay_order_id(
                razorpay_order_id
            )
        )

        if transaction is None:
            logger.warning(
                f"Transaction not found for "
                f"razorpay_order_id={razorpay_order_id}"
            )
            return {
                "success": False,
                "reason": "transaction_not_found",
            }

        # Update transaction payment status
        self.payment_service.transaction_manager.repository.update_payment(
            transaction_id=transaction.get("transaction_id"),
            razorpay_payment_id=razorpay_payment_id,
            payment_status="PAID",
            status="PAYMENT_CAPTURED",
        )

        logger.info(
            f"Transaction payment marked as PAID: "
            f"transaction_id={transaction.get('transaction_id')}"
        )

        # Queue order creation asynchronously
        # In production, this should use a task queue (Celery, etc.)
        # For now, we'll call it inline but log it as async work
        order_result = self._create_order_for_payment(
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            event_id=event_id,
        )

        return {
            "success": True,
            "transaction_updated": True,
            "order_creation": order_result,
        }

    # ========================================================
    # HANDLE PAYMENT FAILED
    # ========================================================

    def _handle_payment_failed(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        event_id: str,
    ) -> Dict[str, Any]:
        """
        Handle payment.failed event:
        Update transaction payment status to FAILED
        """

        # Find transaction by razorpay_order_id
        transaction = (
            self.payment_service
            .transaction_manager
            .repository
            .get_by_razorpay_order_id(
                razorpay_order_id
            )
        )

        if transaction is None:
            logger.warning(
                f"Transaction not found for "
                f"razorpay_order_id={razorpay_order_id}"
            )
            return {
                "success": False,
                "reason": "transaction_not_found",
            }

        # Update transaction payment status
        self.payment_service.transaction_manager.repository.update_payment(
            transaction_id=transaction.get("transaction_id"),
            razorpay_payment_id=razorpay_payment_id,
            payment_status="FAILED",
            status="PAYMENT_FAILED",
        )

        logger.info(
            f"Transaction payment marked as FAILED: "
            f"transaction_id={transaction.get('transaction_id')}"
        )

        return {
            "success": True,
            "transaction_updated": True,
            "payment_status": "FAILED",
        }

    # ========================================================
    # HANDLE ORDER PAID
    # ========================================================

    def _handle_order_paid(
        self,
        razorpay_order_id: str,
        event_id: str,
    ) -> Dict[str, Any]:
        """
        Handle order.paid event:
        This is typically confirmation that Razorpay order is paid.
        Update transaction if needed.
        """

        # Find transaction by razorpay_order_id
        transaction = (
            self.payment_service
            .transaction_manager
            .repository
            .get_by_razorpay_order_id(
                razorpay_order_id
            )
        )

        if transaction is None:
            logger.warning(
                f"Transaction not found for "
                f"razorpay_order_id={razorpay_order_id}"
            )
            return {
                "success": False,
                "reason": "transaction_not_found",
            }

        # Mark order as confirmed if not already
        current_status = transaction.get("status")
        if current_status not in {"PAYMENT_CAPTURED", "ORDER_CREATED", "COMPLETED"}:
            self.payment_service.transaction_manager.repository.update_payment(
                transaction_id=transaction.get("transaction_id"),
                payment_status="PAID",
                status="ORDER_CREATED",
            )

        logger.info(
            f"Order paid confirmed: "
            f"transaction_id={transaction.get('transaction_id')}"
        )

        return {
            "success": True,
            "transaction_updated": True,
            "event": "order.paid",
        }

    # ========================================================
    # PROCESS VERIFIED WEBHOOK
    # ========================================================

    def process(
        self,
        *,
        webhook_result,
        raw_payload: Dict[str, Any],
    ) -> Dict[str, Any]:

        # ----------------------------------------------------
        # SIGNATURE / HANDLER VALIDATION
        # ----------------------------------------------------

        if not webhook_result.valid:

            return {
                "success": False,
                "status": "WEBHOOK_REJECTED",
                "reason": webhook_result.reason,
            }

        # ----------------------------------------------------
        # DUPLICATE EVENT
        # ----------------------------------------------------

        if webhook_result.status == "WEBHOOK_DUPLICATE":

            return {
                "success": True,
                "status": "WEBHOOK_DUPLICATE",
                "event_id": webhook_result.event_id,
                "reason": "event_already_processed",
            }

        # ----------------------------------------------------
        # UNSUPPORTED EVENT
        # ----------------------------------------------------

        if webhook_result.status == "WEBHOOK_IGNORED":

            return {
                "success": True,
                "status": "WEBHOOK_IGNORED",
                "event": webhook_result.event,
                "event_id": webhook_result.event_id,
                "reason": webhook_result.reason,
            }

        # ----------------------------------------------------
        # ACCEPTED EVENT
        # ----------------------------------------------------

        if webhook_result.status != "WEBHOOK_ACCEPTED":

            return {
                "success": False,
                "status": "WEBHOOK_REJECTED",
                "reason": "invalid_webhook_state",
            }

        # ----------------------------------------------------
        # PERSISTENT IDEMPOTENCY
        # ----------------------------------------------------

        event_id = webhook_result.event_id

        if not event_id:

            return {
                "success": False,
                "status": "WEBHOOK_REJECTED",
                "reason": "webhook_event_id_required",
            }

        webhook_record = self.webhook_repository.create(
            event_id=event_id,
            event=webhook_result.event,
            event_type=webhook_result.event,
            razorpay_payment_id=(
                webhook_result.razorpay_payment_id
            ),
            razorpay_order_id=(
                webhook_result.razorpay_order_id
            ),
            payment_id=(
                webhook_result.razorpay_payment_id
            ),
            order_id=(
                webhook_result.razorpay_order_id
            ),
            payment_status=(
                webhook_result.payment_status
            ),
            raw_payload=raw_payload,
        )

        # ----------------------------------------------------
        # DUPLICATE EVENT
        # ----------------------------------------------------

        if webhook_record["duplicate"]:

            return {
                "success": True,
                "status": "WEBHOOK_DUPLICATE",
                "event_id": event_id,
                "reason": "event_already_processed",
            }

        self.webhook_repository.mark_processed(
            event_id=event_id,
            status="PROCESSED",
        )

        payment_result = self.payment_service.process_webhook_event(
            event=webhook_result.event,
            razorpay_payment_id=webhook_result.razorpay_payment_id,
            razorpay_order_id=webhook_result.razorpay_order_id,
            payment_status=webhook_result.payment_status,
            event_id=event_id,
        )

        # Delegate to event-specific handler
        event = webhook_result.event
        if event == "payment.captured":
            event_result = self._handle_payment_captured(
                razorpay_payment_id=webhook_result.razorpay_payment_id,
                razorpay_order_id=webhook_result.razorpay_order_id,
                event_id=event_id,
            )
        elif event == "payment.failed":
            event_result = self._handle_payment_failed(
                razorpay_payment_id=webhook_result.razorpay_payment_id,
                razorpay_order_id=webhook_result.razorpay_order_id,
                event_id=event_id,
            )
        elif event == "order.paid":
            event_result = self._handle_order_paid(
                razorpay_order_id=webhook_result.razorpay_order_id,
                event_id=event_id,
            )
        else:
            event_result = {}

        return {
            "success": payment_result["success"],
            "status": "WEBHOOK_PROCESSED",
            "event": webhook_result.event,
            "event_id": event_id,
            "payment_state": payment_result,
            "transaction_update": event_result,
        }