
"""
AGENTCOMMERCE OS
PHASE 06B — PAYMENT AGENT

Payment preparation / simulation boundary.

IMPORTANT:
- This version does NOT call Razorpay.
- This version does NOT move real money.
- This version simulates payment success/failure.
- Real gateway integration will be added later.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


# ============================================================
# PAYMENT RESULT
# ============================================================

@dataclass
class PaymentResult:

    status: str

    product_id: Optional[int]

    amount: float

    currency: str

    payment_method: str

    transaction_id: Optional[str]

    reason: str


# ============================================================
# PAYMENT AGENT
# ============================================================

class PaymentAgent:

    SUPPORTED_PAYMENT_METHODS = {
        "UPI",
        "CARD",
        "NET_BANKING",
        "WALLET",
    }

    def __init__(self):

        print(
            "Payment Agent initialized."
        )

    # ========================================================
    # PROCESS PAYMENT
    # ========================================================

    def process_payment(
        self,
        product_id: int,
        amount: float,
        payment_method: str = "UPI",
        simulate_failure: bool = False,
    ) -> PaymentResult:

        # ----------------------------------------------------
        # AMOUNT VALIDATION
        # ----------------------------------------------------

        if amount <= 0:

            return PaymentResult(

                status="PAYMENT_FAILED",

                product_id=product_id,

                amount=round(
                    amount,
                    2
                ),

                currency="INR",

                payment_method=payment_method,

                transaction_id=None,

                reason="invalid_amount",
            )

        # ----------------------------------------------------
        # PAYMENT METHOD VALIDATION
        # ----------------------------------------------------

        normalized_method = (
            payment_method.upper()
        )

        if (
            normalized_method
            not in self.SUPPORTED_PAYMENT_METHODS
        ):

            return PaymentResult(

                status="PAYMENT_FAILED",

                product_id=product_id,

                amount=round(
                    amount,
                    2
                ),

                currency="INR",

                payment_method=payment_method,

                transaction_id=None,

                reason="unsupported_payment_method",
            )

        # ----------------------------------------------------
        # SIMULATED FAILURE
        # ----------------------------------------------------

        if simulate_failure:

            return PaymentResult(

                status="PAYMENT_FAILED",

                product_id=product_id,

                amount=round(
                    amount,
                    2
                ),

                currency="INR",

                payment_method=normalized_method,

                transaction_id=None,

                reason="payment_declined",
            )

        # ----------------------------------------------------
        # SIMULATED SUCCESS
        # ----------------------------------------------------

        return PaymentResult(

            status="PAYMENT_SUCCESS",

            product_id=product_id,

            amount=round(
                amount,
                2
            ),

            currency="INR",

            payment_method=normalized_method,

            transaction_id=(
                f"TXN-"
                f"{uuid4().hex[:12].upper()}"
            ),

            reason=(
                "payment_processed_successfully"
            ),
        )


# ============================================================
# LOCAL TEST
# ============================================================

def main():

    agent = PaymentAgent()

    tests = [

        {
            "product_id": 453,
            "amount": 705.81,
            "payment_method": "UPI",
        },

        {
            "product_id": 453,
            "amount": 0,
            "payment_method": "UPI",
        },

        {
            "product_id": 453,
            "amount": 705.81,
            "payment_method": "CASH",
        },

        {
            "product_id": 453,
            "amount": 705.81,
            "payment_method": "UPI",
            "simulate_failure": True,
        },

        {
            "product_id": 453,
            "amount": 705.81,
            "payment_method": "CARD",
        },
    ]

    for test in tests:

        print()
        print("-" * 80)
        print("TEST")
        print("-" * 80)

        print(test)

        result = agent.process_payment(
            **test
        )

        print()
        print(result)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
