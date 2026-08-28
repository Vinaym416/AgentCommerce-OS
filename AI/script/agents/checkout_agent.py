"""
AGENTCOMMERCE OS
PHASE 06 — CHECKOUT AGENT

The Checkout Agent prepares an approved commerce decision
for order creation and payment.

It does NOT execute payment.
"""

from dataclasses import dataclass
from typing import Optional


# ============================================================
# CHECKOUT RESULT
# ============================================================

@dataclass
class CheckoutResult:

    status: str

    product_id: Optional[int]

    original_price: float

    discount_percent: float

    discount_amount: float

    final_price: float

    currency: str

    payment_ready: bool

    reason: str


# ============================================================
# CHECKOUT AGENT
# ============================================================

class CheckoutAgent:

    def __init__(self):

        print("Checkout Agent initialized.")


    # ========================================================
    # PREPARE CHECKOUT
    # ========================================================

    def prepare_checkout(
        self,
        product_id: int,
        product_price: float,
        discount_percent: float = 0.0,
    ):

        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if product_id is None:

            return CheckoutResult(
                status="REJECTED",
                product_id=None,
                original_price=0.0,
                discount_percent=0.0,
                discount_amount=0.0,
                final_price=0.0,
                currency="INR",
                payment_ready=False,
                reason="missing_product_id",
            )


        if product_price <= 0:

            return CheckoutResult(
                status="REJECTED",
                product_id=product_id,
                original_price=product_price,
                discount_percent=0.0,
                discount_amount=0.0,
                final_price=0.0,
                currency="INR",
                payment_ready=False,
                reason="invalid_product_price",
            )


        # ----------------------------------------------------
        # DISCOUNT VALIDATION
        # ----------------------------------------------------

        if discount_percent < 0:

            discount_percent = 0.0


        if discount_percent > 100:

            return CheckoutResult(
                status="REJECTED",
                product_id=product_id,
                original_price=product_price,
                discount_percent=discount_percent,
                discount_amount=0.0,
                final_price=product_price,
                currency="INR",
                payment_ready=False,
                reason="invalid_discount",
            )


        # ----------------------------------------------------
        # CALCULATE CHECKOUT PRICE
        # ----------------------------------------------------

        discount_amount = (
            product_price * discount_percent / 100
        )

        final_price = (
            product_price - discount_amount
        )


        # ----------------------------------------------------
        # ROUNDING
        # ----------------------------------------------------

        discount_amount = round(
            discount_amount,
            2
        )

        final_price = round(
            final_price,
            2
        )


        # ----------------------------------------------------
        # CHECKOUT READY
        # ----------------------------------------------------

        return CheckoutResult(

            status="CHECKOUT_READY",

            product_id=product_id,

            original_price=round(
                product_price,
                2
            ),

            discount_percent=round(
                discount_percent,
                2
            ),

            discount_amount=discount_amount,

            final_price=final_price,

            currency="INR",

            payment_ready=True,

            reason="checkout_prepared_successfully",
        )


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — CHECKOUT AGENT"
    )

    print("=" * 80)


    agent = CheckoutAgent()


    tests = [

        {
            "product_id": 453,
            "price": 784.23,
            "discount": 0,
        },

        {
            "product_id": 453,
            "price": 784.23,
            "discount": 10,
        },

        {
            "product_id": 453,
            "price": 784.23,
            "discount": 15,
        },

        {
            "product_id": 453,
            "price": 784.23,
            "discount": 50,
        },

    ]


    for test in tests:

        print("\n")

        print("-" * 80)

        print("TEST")

        print("-" * 80)

        print(test)


        result = agent.prepare_checkout(

            product_id=test["product_id"],

            product_price=test["price"],

            discount_percent=test["discount"],
        )


        print("\n")

        print(result)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()