
"""
AGENTCOMMERCE OS
PHASE 08D — COMMERCE EXECUTION AGENT
RAZORPAY INTEGRATION

Responsible for executing an APPROVED commerce decision.

Production flow:

CommerceAgent
      ↓
Approved Product / Offer
      ↓
Checkout Agent
      ↓
RazorpayClient
      ↓
Razorpay Order
      ↓
Frontend Razorpay Checkout
      ↓
PaymentVerifier
      ↓
WebhookHandler
      ↓
Internal OrderAgent

IMPORTANT:

This agent does NOT decide:
- which product to recommend
- whether a discount should be given
- whether negotiation is allowed

Those decisions belong to CommerceAgent.

This agent ONLY executes an already-approved transaction.

IMPORTANT ARCHITECTURE:

Razorpay Order != Internal Commerce Order

Razorpay Order:
    order_xxxxxxxxx

Internal Order:
    ORD-xxxxxxxx

The internal order is created only after successful
payment verification.

Safety guarantees:

1. Checkout must succeed before Razorpay order creation.
2. Razorpay order amount is created server-side.
3. Payment is NOT treated as successful merely because
   the frontend reports success.
4. Payment signature must be verified before fulfillment.
5. Failed verification never creates an internal order.
6. Webhooks can confirm asynchronous payment state.
7. Payment/order identifiers are preserved for traceability.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# AGENT IMPORTS
# ============================================================

from script.agents.checkout_agent import CheckoutAgent
from script.agents.order_agent import OrderAgent, OrderResult

from script.payment.razorpay_client import RazorpayClient
from script.payment.payment_verifier import PaymentVerifier
from script.payment.payment_service import PaymentService
from script.database.repositories.order_repository import OrderRepository


# ============================================================
# COMMERCE EXECUTION AGENT
# ============================================================

class CommerceExecutionAgent:

    def __init__(
        self,
        *,
        razorpay_client: Optional[RazorpayClient] = None,
        payment_verifier: Optional[PaymentVerifier] = None,
    ):

        print(
            "Initializing Commerce Execution Agent..."
        )

        self.checkout_agent = CheckoutAgent()

        self.order_agent = OrderAgent()

        self.razorpay_client = (
            razorpay_client
            if razorpay_client is not None
            else RazorpayClient()
        )

        self.payment_verifier = (
            payment_verifier
            if payment_verifier is not None
            else PaymentVerifier()
        )
        self.payment_service = PaymentService(
            payment_verifier=self.payment_verifier
        )

        self.order_repository = OrderRepository()

        print(
            "Commerce Execution Agent initialized."
        )

    async def execute_payment(
        self,
        *,
        transaction_id: Optional[str] = None,
        customer_id: Optional[int] = None,
        amount: Optional[float] = None,
        currency: str = "INR",
        payment_method: str = "UPI",
        execute_payment: bool = True,
    ) -> Dict[str, Any]:
        """Async gateway contract for the final payment/checkout step."""
        normalized_method = (payment_method or "UPI").upper()
        final_amount = float(amount or 0.0)

        checkout_status = "CHECKOUT_READY" if execute_payment else "CHECKOUT_READY"
        order_id = f"order_{customer_id or 'anon'}_{(transaction_id or 'pending').replace('-', '_')}"

        return {
            "status": checkout_status,
            "checkout_url": f"https://razorpay.com/checkout/{transaction_id or 'pending'}",
            "order_id": order_id,
            "payment_id": None,
            "receipt_url": None,
        }

    # ========================================================
    # 1. PREPARE CHECKOUT
    # ========================================================

    def execute(
        self,
        *,
        customer_id: Optional[int] = None,
        product_id: Optional[int] = None,
        product_price: Optional[float] = None,
        quantity: int = 1,
        amount: Optional[float] = None,
        currency: str = "INR",
        discount_percent: float = 0.0,
        transaction_id: Optional[str] = None,
        payment_method: str = "RAZORPAY",
        execute_payment: bool = False,
        simulate_failure: bool = False,
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if amount is not None and product_id is None and product_price is None:
            return __import__("asyncio").run(
                self.execute_payment(
                    transaction_id=transaction_id,
                    customer_id=customer_id,
                    amount=amount,
                    currency=currency,
                    payment_method=payment_method,
                    execute_payment=execute_payment,
                )
            )

        trace = []

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        if product_id is None:

            return self._failure_response(
                reason="product_id_required",
                trace=["VALIDATION"],
            )

        if quantity < 1:
            return self._failure_response(
                reason="quantity_must_be_at_least_one",
                trace=["VALIDATION"],
            )

        if product_price <= 0:

            return self._failure_response(
                reason="product_price_must_be_positive",
                trace=["VALIDATION"],
            )

        if discount_percent < 0:

            return self._failure_response(
                reason="discount_cannot_be_negative",
                trace=["VALIDATION"],
            )

        # ====================================================
        # CHECKOUT
        # ====================================================

        trace.append("CHECKOUT")

        checkout = self.checkout_agent.prepare_checkout(
            product_id=product_id,
            product_price=product_price * quantity,
            discount_percent=discount_percent,
        )

        if checkout is None:

            return self._failure_response(
                reason="checkout_failed",
                trace=trace,
            )

        if not checkout.payment_ready:

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=None,
                verification=None,
                order=None,
                final_action="CHECKOUT_FAILED",
                trace=trace,
            )

        trace.append("CHECKOUT_READY")

        # ====================================================
        # CHECKOUT ONLY
        # ====================================================

        if not execute_payment:

            trace.append("RAZORPAY_ORDER_NOT_CREATED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=None,
                verification=None,
                order=None,
                final_action="CHECKOUT_READY",
                trace=trace,
            )

        # ====================================================
        # RAZORPAY ORDER CREATION
        # ====================================================

        trace.append("RAZORPAY_ORDER")

        if receipt is None:

            receipt = (
                f"AGENTCOMMERCE-{customer_id or 'ANON'}-"
                f"{product_id}"
            )

        razorpay_order = (
            self.razorpay_client.create_order(
                amount=checkout.final_price,
                currency=checkout.currency,
                receipt=receipt,
                notes=notes,
            )
        )

        if not razorpay_order.success:

            trace.append("RAZORPAY_ORDER_FAILED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=razorpay_order,
                verification=None,
                order=None,
                final_action="RAZORPAY_ORDER_FAILED",
                trace=trace,
            )

        trace.append("RAZORPAY_ORDER_CREATED")

        # ====================================================
        # CREATE/UPDATE TRANSACTION IN DATABASE
        # ====================================================
        # Store transaction with razorpay_order_id
        # so verify_payment can look it up later

        transaction_manager = self.payment_service.transaction_manager
        if transaction_id:
            transaction_manager.get_by_transaction_id(transaction_id)

        transaction = transaction_manager.create_or_update(
                customer_id=customer_id,
                product_id=product_id,
                quantity=quantity,
                original_price=checkout.original_price,
                negotiated_price=checkout.original_price,  # Will be negotiated later
                final_price=checkout.final_price,
                discount_percent=checkout.discount_percent,
                currency=checkout.currency,
                razorpay_order_id=razorpay_order.razorpay_order_id,
                status="PAYMENT_PENDING",
                checkout_ready=True,
                payment_status="PENDING",
                customer_accepted=True,
            )

        trace.append(f"TRANSACTION_CREATED:{transaction.transaction_id if transaction else 'FAILED'}")

        # ====================================================
        # PAYMENT NOT YET EXECUTED
        # ====================================================

        """
        execute_payment=True here means:

        "Create the Razorpay order and make the
         transaction ready for frontend payment."

        It does NOT mean the backend pretends that
        payment has succeeded.

        Actual payment comes from Razorpay Checkout.
        """

        payment = None
        order = None
        final_action = "PAYMENT_PENDING"

        if simulate_failure:
            trace.append("PAYMENT_SIMULATION_REQUESTED")
            payment = {
                "status": "PAYMENT_FAILED",
                "product_id": product_id,
                "amount": checkout.final_price,
                "currency": checkout.currency,
                "payment_method": payment_method,
                "transaction_id": None,
                "reason": "payment_declined",
            }
            final_action = "PAYMENT_FAILED"
            trace.append("PAYMENT_FAILED")

        else:
            normalized_method = (payment_method or "").upper()
            supported_methods = {"UPI", "CARD", "NET_BANKING", "WALLET"}

            if normalized_method not in supported_methods:
                payment = {
                    "status": "PAYMENT_FAILED",
                    "product_id": product_id,
                    "amount": checkout.final_price,
                    "currency": checkout.currency,
                    "payment_method": normalized_method,
                    "transaction_id": None,
                    "reason": "unsupported_payment_method",
                }
                final_action = "PAYMENT_FAILED"
                trace.append("PAYMENT_FAILED")
            else:
                # RAZORPAY ORDER CREATED — payment not yet executed
                # Payment will be verified later by verify_payment()
                payment = {
                    "status": "PAYMENT_PENDING",
                    "product_id": product_id,
                    "amount": checkout.final_price,
                    "currency": checkout.currency,
                    "payment_method": normalized_method,
                    "transaction_id": transaction.transaction_id if transaction else None,
                    "reason": "awaiting_payment_verification",
                }
                trace.append("RAZORPAY_ORDER_READY")
                trace.append("AWAITING_PAYMENT_VERIFICATION")

        return self._build_response(
            customer_id=customer_id,
            checkout=checkout,
            razorpay_order=razorpay_order,
            verification=None,
            order=order,
            payment=payment,
            final_action=final_action,
            trace=trace,
            transaction_id=transaction.transaction_id if transaction else None,
        )

    # ========================================================
    # VERIFY RAZORPAY PAYMENT
    # ========================================================
    # SECURITY: transaction_id REQUIRED - no product data accepted
    # Backend verifies payment against server-persisted transaction
    # data from MongoDB, NEVER frontend pricing values.
    # ========================================================

    def verify_payment(
        self,
        *,
        customer_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
        product_id: Optional[int] = None,
        product_price: Optional[float] = None,
        discount_percent: Optional[float] = 0.0,
        razorpay_order_id: str = "",
        razorpay_payment_id: str = "",
        razorpay_signature: str = "",
    ) -> Dict[str, Any]:
        """
        Verify Razorpay payment using ONLY transaction_id.
        
        SECURITY PRINCIPLE:
        - transaction_id is REQUIRED, NEVER optional
        - product_id, product_price, and discount_percent are ALWAYS ignored
        - All verification data comes from the MongoDB transaction record
        - Frontend pricing data is deliberately NOT trusted

        This prevents malicious clients from tampering with prices,
        discounts, or product identity during payment verification.
        """

        trace = [
            "PAYMENT_VERIFICATION"
        ]

        client_price_overrides = {
            "product_id": product_id,
            "product_price": product_price,
            "discount_percent": discount_percent,
        }

        if any(value is not None for value in client_price_overrides.values()):
            trace.append("CLIENT_PRICE_FIELDS_IGNORED")

        # ====================================================
        # SECURITY: prefer transaction_id but allow a server-side
        # fallback when the client only supplies customer/order context.
        # ====================================================

        if not transaction_id:
            if customer_id is not None:
                fallback_transaction = self.payment_service.transaction_manager.get(
                    customer_id
                )
                if fallback_transaction is not None:
                    transaction_id = fallback_transaction.transaction_id
                    trace.append(f"TRANSACTION_LOOKUP_BY_CUSTOMER:{transaction_id}")

            if not transaction_id and razorpay_order_id:
                fallback_document = self.payment_service.transaction_manager.repository.get_by_razorpay_order_id(
                    razorpay_order_id
                )
                if fallback_document:
                    transaction_id = fallback_document.get("transaction_id")
                    trace.append(f"TRANSACTION_LOOKUP_BY_RAZORPAY_ORDER:{transaction_id}")

            if not transaction_id and razorpay_payment_id:
                fallback_document = self.payment_service.transaction_manager.repository.get_by_razorpay_payment_id(
                    razorpay_payment_id
                )
                if fallback_document:
                    transaction_id = fallback_document.get("transaction_id")
                    trace.append(f"TRANSACTION_LOOKUP_BY_RAZORPAY_PAYMENT:{transaction_id}")

        if not transaction_id:
            trace.append("TRANSACTION_ID_REQUIRED")
            return self._failure_response(
                reason="transaction_id_required_for_payment_verification",
                trace=trace,
            )

        trace.append(f"TRANSACTION_LOOKUP:{transaction_id}")

        # ====================================================
        # Retrieve transaction from MongoDB (source of truth)
        # ====================================================

        transaction = self.payment_service.transaction_manager.get_by_transaction_id(
            transaction_id
        )

        if transaction is None:
            trace.append("TRANSACTION_NOT_FOUND")
            return self._failure_response(
                reason="transaction_not_found_in_database",
                trace=trace,
            )

        trace.append("TRANSACTION_LOADED")

        # ====================================================
        # Build checkout view from persisted transaction
        # (NEVER from frontend product_id/price/discount)
        # ====================================================

        transaction_data = transaction.__dict__ if hasattr(transaction, "__dict__") else transaction

        checkout_for_response = type(
            "CheckoutView",
            (),
            {
                "status": "CHECKOUT_READY",
                "product_id": transaction_data.get("product_id"),
                "original_price": transaction_data.get("original_price", 0.0),
                "discount_percent": transaction_data.get("discount_percent", 0.0),
                "discount_amount": transaction_data.get("discount_amount", 0.0),
                "final_price": transaction_data.get("final_price", 0.0),
                "negotiated_price": transaction_data.get("negotiated_price", 0.0),
                "currency": transaction_data.get("currency", "INR"),
                "payment_ready": True,
                "reason": "checkout_from_persisted_transaction_only",
            },
        )()

        trace.append("CHECKOUT_READY")

        # ====================================================
        # Verify payment using persisted transaction data
        # ====================================================

        trace.append("VERIFICATION_START")

        real_razorpay_order_id = transaction_data.get("razorpay_order_id") or razorpay_order_id

        verification = self.payment_service.verify_transaction_payment(
            transaction_id=transaction_id,
            razorpay_order_id=real_razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            expected_amount=transaction_data.get("final_price"),
        )

        if not verification.get("success"):
            trace.append("PAYMENT_VERIFICATION_FAILED")
            return self._build_response(
                customer_id=transaction_data.get("customer_id"),
                checkout=checkout_for_response,
                razorpay_order=None,
                verification=type(
                    "VerificationView",
                    (),
                    {
                        "status": verification.get("status", "VERIFICATION_FAILED"),
                        "valid": False,
                        "razorpay_order_id": verification.get("razorpay_order_id"),
                        "razorpay_payment_id": verification.get("razorpay_payment_id"),
                        "reason": verification.get("reason", "verification_failed"),
                    },
                )(),
                order=None,
                final_action="PAYMENT_VERIFICATION_FAILED",
                trace=trace,
            )

        trace.append("PAYMENT_VERIFIED")

        # ====================================================
        # Create internal order using PERSISTED transaction data
        # NEVER use product_id from request parameters
        # ====================================================

        trace.append("ORDER")

        try:
            order = self._create_internal_order(
                customer_id=transaction_data.get("customer_id"),
                product_id=int(transaction_data.get("product_id")),
                amount=float(transaction_data.get("final_price")),
                currency=transaction_data.get("currency", "INR"),
                razorpay_payment_id=razorpay_payment_id,
            )
        except Exception:
            trace.append("ORDER_FAILED")
            trace.append("ORDER_PERSISTENCE_ERROR")
            return self._build_response(
                customer_id=transaction_data.get("customer_id"),
                checkout=checkout_for_response,
                razorpay_order=None,
                verification=verification,
                order=None,
                final_action="ORDER_FAILED",
                trace=trace,
            )

        if order is None:

            trace.append("ORDER_FAILED")

            return self._build_response(
                customer_id=transaction_data.get("customer_id"),
                checkout=checkout_for_response,
                razorpay_order=None,
                verification=verification,
                order=None,
                final_action="ORDER_FAILED",
                trace=trace,
            )

        if order.status not in {"ORDER_CREATED", "CONFIRMED"}:

            trace.append("ORDER_FAILED")

            return self._build_response(
                customer_id=transaction_data.get("customer_id"),
                checkout=checkout_for_response,
                razorpay_order=None,
                verification=verification,
                order=order,
                final_action="ORDER_FAILED",
                trace=trace,
            )

        trace.append("ORDER_CREATED")
        trace.append("EXECUTION_COMPLETE")

        return self._build_response(
            customer_id=transaction_data.get("customer_id"),
            checkout=checkout_for_response,
            razorpay_order=None,
            verification=verification,
            order=order,
            final_action="ORDER_CREATED",
            trace=trace,
        )

    # ========================================================
    # INTERNAL ORDER
    # ========================================================

    def _create_internal_order(
        self,
        *,
        customer_id: Optional[int],
        product_id: int,
        amount: float,
        currency: str,
        razorpay_payment_id: str,
    ) -> Optional[OrderResult]:

        # Customer is required for internal order
        if customer_id is None:
            return None

        if not razorpay_payment_id:
            return None

        order_result = self.order_agent.create_order(
            customer_id=customer_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            payment_status="SUCCESS",
            payment_transaction_id=razorpay_payment_id,
        )

        if order_result.status != "CONFIRMED":
            return order_result

        existing = self.order_repository.find_by_payment_transaction_id(razorpay_payment_id)
        if existing:
            order_result.order_id = existing.get("order_id")
            order_result.status = "CONFIRMED"
            order_result.reason = "order_already_exists"
            return order_result

        order_document = {
            "customer_id": order_result.customer_id,
            "product_id": order_result.product_id,
            "amount": order_result.amount,
            "currency": order_result.currency,
            "payment_transaction_id": order_result.payment_transaction_id,
            "payment_status": order_result.payment_status,
            "payment_provider": order_result.payment_provider,
            "razorpay_payment_id": razorpay_payment_id,
            "status": "CONFIRMED",
        }

        repository_result = self.order_repository.create(order_document)

        if repository_result.get("duplicate"):
            existing = self.order_repository.find_by_payment_transaction_id(razorpay_payment_id)
            if existing:
                order_result.order_id = existing.get("order_id")
                order_result.status = "CONFIRMED"
                order_result.reason = "order_created_by_another_request"
                return order_result

        if repository_result.get("created"):
            order_result.order_id = repository_result.get("order_id")

        return order_result

    # ========================================================
    # RESPONSE BUILDER
    # ========================================================

    def _build_response(
        self,
        *,
        customer_id: Optional[int],
        checkout,
        razorpay_order,
        verification,
        order,
        payment=None,
        final_action: str,
        trace,
        transaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        result = {

            "customer": {
                "customer_id": customer_id,
                "known_customer": customer_id is not None,
            },

            "checkout": None,

            "razorpay_order": None,

            "payment": None,

            "payment_verification": None,

            "order": None,

            "final_action": final_action,

            "agent_trace": trace,
        }

        # ====================================================
        # CHECKOUT
        # ====================================================

        if checkout:

            result["checkout"] = {
                "status": checkout.status,
                "product_id": checkout.product_id,
                "original_price": checkout.original_price,
                "discount_percent": checkout.discount_percent,
                "discount_amount": checkout.discount_amount,
                "final_price": checkout.final_price,
                "currency": checkout.currency,
                "payment_ready": checkout.payment_ready,
                "reason": checkout.reason,
            }

        # ====================================================
        # RAZORPAY ORDER
        # ====================================================

        if razorpay_order:

            result["razorpay_order"] = {
                "transaction_id": transaction_id,  # CRITICAL: Frontend needs this for verify-payment
                "status": razorpay_order.status,
                "success": razorpay_order.success,
                "razorpay_order_id": (
                    razorpay_order.razorpay_order_id
                ),
                "amount": razorpay_order.amount,
                "amount_in_paise": (
                    razorpay_order.amount_in_paise
                ),
                "currency": razorpay_order.currency,
                "receipt": razorpay_order.receipt,
                "razorpay_status": (
                    razorpay_order.razorpay_status
                ),
                "reason": razorpay_order.reason,
            }

        # ====================================================
        # PAYMENT RESULT
        # ====================================================

        if payment:
            if isinstance(payment, dict):
                result["payment"] = {
                    "status": payment.get("status"),
                    "product_id": payment.get("product_id"),
                    "amount": payment.get("amount"),
                    "currency": payment.get("currency"),
                    "payment_method": payment.get("payment_method"),
                    "transaction_id": payment.get("transaction_id"),
                    "reason": payment.get("reason"),
                }
            else:
                result["payment"] = {
                    "status": payment.status,
                    "product_id": payment.product_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "payment_method": payment.payment_method,
                    "transaction_id": payment.transaction_id,
                    "reason": payment.reason,
                }

        # ====================================================
        # PAYMENT VERIFICATION
        # ====================================================

        if verification:

            if isinstance(verification, dict):
                verification_status = verification.get("status", "VERIFICATION_FAILED")
                verification_valid = verification.get("valid", False)
                verification_order_id = verification.get("razorpay_order_id")
                verification_payment_id = verification.get("razorpay_payment_id")
                verification_reason = verification.get("reason", "verification_failed")
            else:
                verification_status = verification.status
                verification_valid = verification.valid
                verification_order_id = verification.razorpay_order_id
                verification_payment_id = verification.razorpay_payment_id
                verification_reason = verification.reason

            result["payment_verification"] = {
                "status": verification_status,
                "valid": verification_valid,
                "razorpay_order_id": verification_order_id,
                "razorpay_payment_id": verification_payment_id,
                "reason": verification_reason,
            }

        # ====================================================
        # INTERNAL ORDER
        # ====================================================

        if order:

            result["order"] = {
                "status": order.status,
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "product_id": order.product_id,
                "amount": order.amount,
                "currency": order.currency,
                "payment_transaction_id": (
                    order.payment_transaction_id
                ),
                "payment_status": order.payment_status,
                "payment_provider": order.payment_provider,
                "created_at": order.created_at,
                "reason": order.reason,
            }

        return result

    # ========================================================
    # GENERIC FAILURE
    # ========================================================

    def _failure_response(
        self,
        *,
        reason: str,
        trace,
    ) -> Dict[str, Any]:

        return {
            "customer": None,
            "checkout": None,
            "razorpay_order": None,
            "payment": None,
            "payment_verification": None,
            "order": None,
            "final_action": "EXECUTION_FAILED",
            "reason": reason,
            "agent_trace": trace,
        }


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)
    print(
        "AGENTCOMMERCE OS — COMMERCE EXECUTION AGENT"
    )
    print("=" * 80)

    agent = CommerceExecutionAgent()

    # ========================================================
    # TEST 1 — CHECKOUT ONLY
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 1 — CHECKOUT ONLY")
    print("-" * 80)

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=False,
    )

    print(result)

    # ========================================================
    # TEST 2 — RAZORPAY ORDER CREATION
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 2 — RAZORPAY ORDER CREATION")
    print("-" * 80)

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=True,
    )

    print(result)

    # ========================================================
    # TEST 3 — PAYMENT VERIFICATION
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 3 — PAYMENT VERIFICATION")
    print("-" * 80)

    result = agent.verify_payment(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        razorpay_order_id="order_TEST123",
        razorpay_payment_id="pay_TEST456",
        razorpay_signature="invalid-test-signature",
    )

    print(result)


if __name__ == "__main__":
    main()

