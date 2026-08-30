"""
AGENTCOMMERCE OS
PHASE 12C — PAYMENT SERVICE

Coordinates:

Webhook event
    ↓
Payment State Machine
    ↓
Payment Repository

The state machine owns state-transition rules.
The service owns orchestration/persistence.
"""

from dataclasses import asdict
from typing import Optional, Dict, Any

from script.payment.payment_state_machine import (
    PaymentStateMachine,
)
from script.payment.payment_verifier import PaymentVerifier
from script.database.repositories.payment_repository import (
    PaymentRepository,
)
from script.transaction.transaction_manager import TransactionManager


class PaymentService:

    def __init__(
        self,
        payment_repository: Optional[PaymentRepository] = None,
        payment_verifier: Optional[PaymentVerifier] = None,
        transaction_manager: Optional[TransactionManager] = None,
    ):

        self.payment_repository = (
            payment_repository
            or PaymentRepository()
        )
        self.payment_verifier = (
            payment_verifier
            or PaymentVerifier()
        )
        self.transaction_manager = (
            transaction_manager
            or TransactionManager()
        )

    @staticmethod
    def _normalize_transaction(transaction):
        if transaction is None:
            return {}

        if isinstance(transaction, dict):
            return dict(transaction)

        payload = {}

        try:
            payload.update(asdict(transaction))
        except (TypeError, ValueError):
            pass

        for source in (
            getattr(transaction, "__dict__", {}),
            getattr(transaction.__class__, "__dict__", {}),
        ):
            for key, value in getattr(source, "items", lambda: [])():
                if key.startswith("_"):
                    continue
                if callable(value):
                    continue
                payload.setdefault(key, value)

        for name in getattr(type(transaction), "__annotations__", {}):
            if name not in payload and hasattr(transaction, name):
                payload[name] = getattr(transaction, name)

        return payload

    # ========================================================
    # VERIFY TRANSACTION PAYMENT
    # ========================================================

    def verify_transaction_payment(
        self,
        *,
        transaction_id: Optional[str],
        razorpay_order_id: Optional[str],
        razorpay_payment_id: Optional[str],
        razorpay_signature: Optional[str],
        expected_amount: Optional[float] = None,
    ) -> Dict[str, Any]:

        if not transaction_id:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "transaction_id_required",
            }

        transaction = (
            self.transaction_manager
            .get_by_transaction_id(
                transaction_id
            )
        )
        transaction_payload = self._normalize_transaction(transaction)

        if transaction is None:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "transaction_not_found",
            }

        stored_razorpay_order_id = (
            transaction_payload.get("razorpay_order_id")
        )

        if not stored_razorpay_order_id:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "stored_razorpay_order_id_missing",
            }

        if razorpay_order_id and stored_razorpay_order_id != razorpay_order_id:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "razorpay_order_id_mismatch",
            }

        stored_amount = transaction_payload.get("final_price")
        if expected_amount is not None:
            stored_amount = expected_amount

        if stored_amount is None:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "stored_amount_missing",
            }

        verification_order_id = stored_razorpay_order_id

        verification = self.payment_verifier.verify_payment_signature(
            razorpay_order_id=verification_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not verification.valid:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": verification.reason,
                "razorpay_order_id": verification_order_id,
                "razorpay_payment_id": razorpay_payment_id,
            }

        # Server-authoritative amount check: never trust frontend price values.
        if expected_amount is not None and abs(float(expected_amount) - float(stored_amount)) > 0.01:
            return {
                "success": False,
                "status": "VERIFICATION_FAILED",
                "valid": False,
                "reason": "amount_mismatch",
                "razorpay_order_id": verification_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "amount": stored_amount,
            }

        self.transaction_manager.create_or_update(
            customer_id=transaction_payload.get("customer_id"),
            transaction_id=transaction_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=verification_order_id,
            payment_status="PAID",
            status="PAYMENT_CAPTURED",
        )

        repository = getattr(self.transaction_manager, "repository", None)
        if repository is not None and hasattr(repository, "update_payment"):
            repository.update_payment(
                transaction_id=transaction_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=verification_order_id,
                payment_status="PAID",
                status="PAYMENT_CAPTURED",
            )

        return {
            "success": True,
            "status": "PAYMENT_VERIFIED",
            "valid": True,
            "transaction_id": transaction_id,
            "razorpay_order_id": verification_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "amount": stored_amount,
            "reason": "payment_verified_successfully",
        }

    # ========================================================
    # PROCESS WEBHOOK EVENT
    # ========================================================

    def process_webhook_event(
        self,
        event: str,
        razorpay_payment_id: Optional[str],
        razorpay_order_id: Optional[str],
        payment_status: Optional[str],
        event_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not event:

            return {
                "success": False,
                "reason": "event_missing",
            }

        # ----------------------------------------------------
        # FIND EXISTING PAYMENT
        # ----------------------------------------------------

        payment = None

        if razorpay_payment_id:

            payment = (
                self.payment_repository
                .find_by_razorpay_payment_id(
                    razorpay_payment_id
                )
            )

        # ----------------------------------------------------
        # CREATE INITIAL PAYMENT RECORD
        # ----------------------------------------------------

        if payment is None:

            payment = {

                "transaction_id":
                    transaction_id,

                "razorpay_payment_id":
                    razorpay_payment_id,

                "razorpay_order_id":
                    razorpay_order_id,

                "payment_state":
                    "CREATED",

                "payment_status":
                    payment_status,

                "last_event_id":
                    event_id,
            }

            self.payment_repository.create(
                payment
            )

            current_state = "CREATED"

        else:

            current_state = (
                payment.get(
                    "payment_state",
                    "CREATED"
                )
            )

        # ----------------------------------------------------
        # STATE MACHINE
        # ----------------------------------------------------

        machine = PaymentStateMachine(
            initial_state=current_state
        )

        result = machine.apply_event(
            event
        )

        # ----------------------------------------------------
        # PERSIST STATE
        # ----------------------------------------------------

        if result.success and result.changed:

            self.payment_repository.update_state(
                razorpay_payment_id=(
                    razorpay_payment_id
                ),
                payment_state=(
                    result.current_state
                ),
                event=event,
                event_id=event_id,
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        return {

            "success":
                result.success,

            "changed":
                result.changed,

            "previous_state":
                result.previous_state,

            "current_state":
                result.current_state,

            "reason":
                result.reason,

            "event":
                event,

            "event_id":
                event_id,

        }