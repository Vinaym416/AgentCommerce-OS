
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

        print(
            "Commerce Execution Agent initialized."
        )

    # ========================================================
    # 1. PREPARE CHECKOUT
    # ========================================================

    def execute(
        self,
        *,
        customer_id: Optional[int],
        product_id: int,
        product_price: float,
        discount_percent: float = 0.0,
        payment_method: str = "RAZORPAY",
        execute_payment: bool = False,
        simulate_failure: bool = False,
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        trace = []

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        if product_id is None:

            return self._failure_response(
                reason="product_id_required",
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
            product_price=product_price,
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

        if simulate_failure:

            trace.append("PAYMENT_SIMULATION_REQUESTED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=razorpay_order,
                verification=None,
                order=None,
                final_action="PAYMENT_PENDING",
                trace=trace,
            )

        trace.append("PAYMENT_PENDING")

        return self._build_response(
            customer_id=customer_id,
            checkout=checkout,
            razorpay_order=razorpay_order,
            verification=None,
            order=None,
            final_action="PAYMENT_PENDING",
            trace=trace,
        )

    # ========================================================
    # VERIFY RAZORPAY PAYMENT
    # ========================================================

    def verify_payment(
        self,
        *,
        customer_id: Optional[int],
        product_id: int,
        product_price: float,
        discount_percent: float,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Dict[str, Any]:

        trace = [
            "PAYMENT_VERIFICATION"
        ]

        # ====================================================
        # CHECKOUT RECONSTRUCTION
        # ====================================================

        checkout = self.checkout_agent.prepare_checkout(
            product_id=product_id,
            product_price=product_price,
            discount_percent=discount_percent,
        )

        if checkout is None:

            return self._failure_response(
                reason="checkout_failed",
                trace=trace,
            )

        trace.append("CHECKOUT_READY")

        # ====================================================
        # SIGNATURE VERIFICATION
        # ====================================================

        trace.append("SIGNATURE_VERIFICATION")

        verification = (
            self.payment_verifier.verify_payment_signature(
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
            )
        )

        if not verification.valid:

            trace.append("PAYMENT_VERIFICATION_FAILED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=None,
                verification=verification,
                order=None,
                final_action="PAYMENT_VERIFICATION_FAILED",
                trace=trace,
            )

        trace.append("PAYMENT_VERIFIED")

        # ====================================================
        # INTERNAL ORDER CREATION
        # ====================================================

        trace.append("ORDER")

        order = self._create_internal_order(
            customer_id=customer_id,
            product_id=product_id,
            amount=checkout.final_price,
            currency=checkout.currency,
            razorpay_payment_id=razorpay_payment_id,
        )

        if order is None:

            trace.append("ORDER_FAILED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=None,
                verification=verification,
                order=None,
                final_action="ORDER_FAILED",
                trace=trace,
            )

        if order.status != "ORDER_CREATED":

            trace.append("ORDER_FAILED")

            return self._build_response(
                customer_id=customer_id,
                checkout=checkout,
                razorpay_order=None,
                verification=verification,
                order=order,
                final_action="ORDER_FAILED",
                trace=trace,
            )

        trace.append("ORDER_CREATED")
        trace.append("EXECUTION_COMPLETE")

        return self._build_response(
            customer_id=customer_id,
            checkout=checkout,
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

        return self.order_agent.create_order(
            customer_id=customer_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            payment_status="SUCCESS",
            payment_transaction_id=razorpay_payment_id,
        )

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
        final_action: str,
        trace,
    ) -> Dict[str, Any]:

        result = {

            "customer": {
                "customer_id": customer_id,
                "known_customer": customer_id is not None,
            },

            "checkout": None,

            "razorpay_order": None,

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
        # PAYMENT VERIFICATION
        # ====================================================

        if verification:

            result["payment_verification"] = {
                "status": verification.status,
                "valid": verification.valid,
                "razorpay_order_id": (
                    verification.razorpay_order_id
                ),
                "razorpay_payment_id": (
                    verification.razorpay_payment_id
                ),
                "reason": verification.reason,
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

