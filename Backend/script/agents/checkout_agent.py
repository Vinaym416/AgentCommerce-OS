"""
AGENTCOMMERCE OS
PHASE 06 — CHECKOUT AGENT

The Checkout Agent prepares an approved commerce decision
for order creation and payment.

It does NOT execute payment.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


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

        try:
            product_price = float(product_price)
        except (TypeError, ValueError):
            return CheckoutResult(
                status="REJECTED",
                product_id=product_id,
                original_price=0.0,
                discount_percent=0.0,
                discount_amount=0.0,
                final_price=0.0,
                currency="INR",
                payment_ready=False,
                reason="invalid_product_price",
            )

        if product_price <= 0:

            return CheckoutResult(
                status="REJECTED",
                product_id=product_id,
                original_price=round(product_price, 2),
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

        try:
            discount_percent = float(discount_percent)
        except (TypeError, ValueError):
            discount_percent = 0.0

        if discount_percent < 0:
            discount_percent = 0.0

        if discount_percent > 100:

            return CheckoutResult(
                status="REJECTED",
                product_id=product_id,
                original_price=round(product_price, 2),
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

    # ========================================================
    # CREATE CHECKOUT SESSION
    # ========================================================

    def create_checkout(
        self,
        *,
        customer_id: Optional[int],
        product: dict,
        quantity: int = 1,
        discount_percent: float = 0.0,
    ) -> dict:

        if not product:
            raise ValueError("Product is required for checkout.")

        if quantity < 1:
            raise ValueError("Quantity must be at least 1.")

        product_id = product.get("product_id")
        price = product.get("price")

        if product_id is None:
            raise ValueError("Product ID is required.")

        if price is None:
            raise ValueError("Product price is required.")

        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValueError("Product price must be numeric.")

        if price <= 0:
            raise ValueError("Product price must be greater than zero.")

        try:
            discount_percent = float(discount_percent)
        except (TypeError, ValueError):
            discount_percent = 0.0

        if discount_percent < 0:
            discount_percent = 0.0

        if discount_percent > 100:
            discount_percent = 100.0

        subtotal = price * quantity
        discount_amount = subtotal * discount_percent / 100.0
        final_price = subtotal - discount_amount

        subtotal = round(subtotal, 2)
        discount_amount = round(discount_amount, 2)
        final_price = round(final_price, 2)

        checkout_id = f"checkout_{uuid4().hex[:12]}"

        return {
            "checkout_id": checkout_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "currency": "INR",
            "unit_price": round(price, 2),
            "subtotal": subtotal,
            "discount_percent": round(discount_percent, 2),
            "discount_amount": discount_amount,
            "final_price": final_price,
            "status": "READY_FOR_PAYMENT",
            "payment_required": True,
            "payment_executed": False,
            "order_created": False,
        }


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