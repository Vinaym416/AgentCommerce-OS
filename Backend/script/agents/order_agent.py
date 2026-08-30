
"""
AGENTCOMMERCE OS
PHASE 06C — ORDER AGENT

Responsible for creating a commerce order
after successful payment.

Flow:

Checkout
   ↓
Payment
   ↓
Order Agent
   ↓
Order Created
   ↓
Order Confirmation

IMPORTANT:
- The Order Agent does NOT process payments.
- An order can only be created after successful payment.
- Failed/invalid payments never create orders.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


# ============================================================
# ORDER RESULT
# ============================================================

@dataclass
class OrderResult:

    status: str

    order_id: Optional[str]

    customer_id: Optional[int]

    product_id: Optional[int]

    amount: float

    currency: str

    payment_transaction_id: Optional[str]

    payment_status: str

    payment_provider: str

    created_at: str

    reason: str


# ============================================================
# ORDER AGENT
# ============================================================

class OrderAgent:

    def __init__(self):

        print(
            "Order Agent initialized."
        )

    # ========================================================
    # CREATE ORDER
    # ========================================================

    def create_order(
        self,
        customer_id: Optional[int],
        product_id: Optional[int],
        amount: float,
        currency: str = "INR",
        payment_status: str = "SUCCESS",
        payment_transaction_id: Optional[str] = None,
    ) -> OrderResult:

        # ----------------------------------------------------
        # PAYMENT MUST BE SUCCESSFUL
        # ----------------------------------------------------

        if payment_status != "SUCCESS":

            return self._failure(
                customer_id=customer_id,
                product_id=product_id,
                amount=amount,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="order_requires_successful_payment",
            )

        # ----------------------------------------------------
        # SUCCESSFUL PAYMENT MUST HAVE TRANSACTION ID
        # ----------------------------------------------------

        if not payment_transaction_id:

            return self._failure(
                customer_id=customer_id,
                product_id=product_id,
                amount=amount,
                currency=currency,
                payment_transaction_id=None,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="payment_transaction_id_required",
            )

        # ----------------------------------------------------
        # CUSTOMER VALIDATION
        # ----------------------------------------------------

        if customer_id is None:

            return self._failure(
                customer_id=None,
                product_id=product_id,
                amount=amount,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="customer_id_required",
            )

        # ----------------------------------------------------
        # PRODUCT VALIDATION
        # ----------------------------------------------------

        if product_id is None:

            return self._failure(
                customer_id=customer_id,
                product_id=None,
                amount=amount,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="product_id_required",
            )

        # ----------------------------------------------------
        # AMOUNT VALIDATION
        # ----------------------------------------------------

        try:
            amount = float(amount)

        except (TypeError, ValueError):

            return self._failure(
                customer_id=customer_id,
                product_id=product_id,
                amount=0.0,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="invalid_order_amount",
            )

        if amount <= 0:

            return self._failure(
                customer_id=customer_id,
                product_id=product_id,
                amount=amount,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="order_amount_must_be_positive",
            )

        # ----------------------------------------------------
        # CURRENCY VALIDATION
        # ----------------------------------------------------

        if not currency:

            return self._failure(
                customer_id=customer_id,
                product_id=product_id,
                amount=amount,
                currency=currency,
                payment_transaction_id=payment_transaction_id,
                payment_status=payment_status,
                payment_provider="RAZORPAY",
                reason="currency_required",
            )

        currency = currency.upper()

        # ----------------------------------------------------
        # GENERATE ORDER ID
        # ----------------------------------------------------

        order_id = (
            "ORD-"
            + uuid4().hex[:10].upper()
        )

        # ----------------------------------------------------
        # CREATE ORDER
        # ----------------------------------------------------

        return OrderResult(

            status="CONFIRMED",

            order_id=order_id,

            customer_id=customer_id,

            product_id=product_id,

            amount=round(
                amount,
                2,
            ),

            currency=currency,

            payment_transaction_id=(
                payment_transaction_id
            ),

            payment_status="SUCCESS",

            payment_provider="RAZORPAY",

            created_at=self._timestamp(),

            reason=(
                "order_created_after_successful_payment"
            ),
        )

    # ========================================================
    # FAILURE RESULT
    # ========================================================

    def _failure(
        self,
        *,
        customer_id,
        product_id,
        amount,
        currency,
        payment_transaction_id,
        payment_status,
        payment_provider,
        reason,
    ) -> OrderResult:

        try:
            normalized_amount = round(
                float(amount),
                2,
            )

        except (TypeError, ValueError):
            normalized_amount = 0.0

        return OrderResult(

            status="ORDER_NOT_CREATED",

            order_id=None,

            customer_id=customer_id,

            product_id=product_id,

            amount=normalized_amount,

            currency=currency,

            payment_transaction_id=(
                payment_transaction_id
            ),

            payment_status=payment_status,

            payment_provider=payment_provider,

            created_at=self._timestamp(),

            reason=reason,
        )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    def _timestamp(self) -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — ORDER AGENT"
    )

    print("=" * 80)

    agent = OrderAgent()

    # --------------------------------------------------------
    # TEST 1 — SUCCESSFUL PAYMENT
    # --------------------------------------------------------

    print("\n")
    print("-" * 80)
    print("TEST 1 — SUCCESSFUL PAYMENT")
    print("-" * 80)

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-TEST-001",
    )

    print(result)

    # --------------------------------------------------------
    # TEST 2 — FAILED PAYMENT
    # --------------------------------------------------------

    print("\n")
    print("-" * 80)
    print("TEST 2 — FAILED PAYMENT")
    print("-" * 80)

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="FAILED",

        payment_transaction_id="TXN-TEST-002",
    )

    print(result)

    # --------------------------------------------------------
    # TEST 3 — INVALID AMOUNT
    # --------------------------------------------------------

    print("\n")
    print("-" * 80)
    print("TEST 3 — INVALID AMOUNT")
    print("-" * 80)

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=0,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-TEST-003",
    )

    print(result)

    # --------------------------------------------------------
    # TEST 4 — SUCCESS WITHOUT TRANSACTION ID
    # --------------------------------------------------------

    print("\n")
    print("-" * 80)
    print("TEST 4 — SUCCESS WITHOUT TRANSACTION ID")
    print("-" * 80)

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id=None,
    )

    print(result)


if __name__ == "__main__":

    main()

