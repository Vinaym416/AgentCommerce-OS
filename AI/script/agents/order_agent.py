"""
AGENTCOMMERCE OS
PHASE 06 — ORDER AGENT

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
The Order Agent does NOT process payments.
It only creates an order after payment success.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional


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
        customer_id: int,
        product_id: int,
        amount: float,
        currency: str = "INR",
        payment_status: str = "SUCCESS",
        payment_transaction_id: Optional[str] = None,
    ) -> OrderResult:

        # ----------------------------------------------------
        # PAYMENT VALIDATION
        # ----------------------------------------------------

        if payment_status != "SUCCESS":

            return OrderResult(

                status="ORDER_NOT_CREATED",

                order_id=None,

                customer_id=customer_id,

                product_id=product_id,

                amount=amount,

                currency=currency,

                payment_transaction_id=(
                    payment_transaction_id
                ),

                created_at=self._timestamp(),

                reason=(
                    "order_requires_successful_payment"
                )
            )

        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if customer_id is None:

            return OrderResult(

                status="ORDER_NOT_CREATED",

                order_id=None,

                customer_id=None,

                product_id=product_id,

                amount=amount,

                currency=currency,

                payment_transaction_id=(
                    payment_transaction_id
                ),

                created_at=self._timestamp(),

                reason=(
                    "customer_id_required"
                )
            )

        if product_id is None:

            return OrderResult(

                status="ORDER_NOT_CREATED",

                order_id=None,

                customer_id=customer_id,

                product_id=None,

                amount=amount,

                currency=currency,

                payment_transaction_id=(
                    payment_transaction_id
                ),

                created_at=self._timestamp(),

                reason=(
                    "product_id_required"
                )
            )

        if amount <= 0:

            return OrderResult(

                status="ORDER_NOT_CREATED",

                order_id=None,

                customer_id=customer_id,

                product_id=product_id,

                amount=amount,

                currency=currency,

                payment_transaction_id=(
                    payment_transaction_id
                ),

                created_at=self._timestamp(),

                reason=(
                    "order_amount_must_be_positive"
                )
            )

        # ----------------------------------------------------
        # CREATE ORDER ID
        # ----------------------------------------------------

        order_id = (
            "ORD-"
            + uuid4().hex[:10].upper()
        )

        # ----------------------------------------------------
        # CREATE ORDER
        # ----------------------------------------------------

        return OrderResult(

            status="ORDER_CREATED",

            order_id=order_id,

            customer_id=customer_id,

            product_id=product_id,

            amount=round(
                float(amount),
                2
            ),

            currency=currency,

            payment_transaction_id=(
                payment_transaction_id
            ),

            created_at=self._timestamp(),

            reason=(
                "order_created_after_successful_payment"
            )
        )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    def _timestamp(self) -> str:

        return (
            datetime.now(
                timezone.utc
            ).isoformat()
        )


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

        payment_transaction_id="TXN-TEST-001"
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

        payment_transaction_id="TXN-TEST-002"
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

        payment_transaction_id="TXN-TEST-003"
    )

    print(result)


if __name__ == "__main__":

    main()