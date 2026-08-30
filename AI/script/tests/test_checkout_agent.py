
"""
AGENTCOMMERCE OS
PHASE 06A — CHECKOUT AGENT TEST SUITE
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from script.agents.checkout_agent import CheckoutAgent


# ============================================================
# TEST STATE
# ============================================================

passed = 0
failed = 0


def check(
    test_name,
    condition,
    expected=None,
    actual=None,
):

    global passed, failed

    if condition:

        passed += 1

        print(
            f"[PASS] {test_name}"
        )

    else:

        failed += 1

        print(
            f"[FAIL] {test_name}"
        )

        if expected is not None:

            print(
                f"       Expected: {expected}"
            )

        if actual is not None:

            print(
                f"       Actual:   {actual}"
            )


# ============================================================
# TEST PRODUCT
# ============================================================

PRODUCT = {

    "product_id": 64,

    "price": 713.93,

    "rating": 4.03,

    "product_score": 0.596,
}


# ============================================================
# 1. BASIC CHECKOUT
# ============================================================

def test_basic_checkout():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=1,

        discount_percent=0,
    )

    check(
        "Checkout returns dictionary",
        isinstance(result, dict),
    )

    check(
        "Checkout ID exists",
        bool(result.get("checkout_id")),
    )

    check(
        "Customer ID preserved",
        result.get("customer_id") == 5176,
    )

    check(
        "Product ID preserved",
        result.get("product_id") == 64,
    )


# ============================================================
# 2. PRICE CALCULATION
# ============================================================

def test_price_calculation():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=1,

        discount_percent=0,
    )

    check(
        "Unit price correct",
        result.get("unit_price")
        == 713.93,
    )

    check(
        "Subtotal correct",
        result.get("subtotal")
        == 713.93,
    )

    check(
        "Zero discount amount",
        result.get("discount_amount")
        == 0.0,
    )

    check(
        "Final price correct",
        result.get("final_price")
        == 713.93,
    )


# ============================================================
# 3. DISCOUNT CALCULATION
# ============================================================

def test_discount():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=1,

        discount_percent=10,
    )

    check(
        "Discount percentage preserved",
        result.get("discount_percent")
        == 10.0,
    )

    check(
        "Discount amount calculated",
        result.get("discount_amount")
        == 71.39,
    )

    check(
        "Final price calculated",
        result.get("final_price")
        == 642.54,
    )


# ============================================================
# 4. QUANTITY
# ============================================================

def test_quantity():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=2,

        discount_percent=0,
    )

    check(
        "Quantity preserved",
        result.get("quantity")
        == 2,
    )

    check(
        "Subtotal handles quantity",
        result.get("subtotal")
        == 1427.86,
    )

    check(
        "Final price handles quantity",
        result.get("final_price")
        == 1427.86,
    )


# ============================================================
# 5. PAYMENT SAFETY
# ============================================================

def test_payment_safety():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=1,

        discount_percent=10,
    )

    check(
        "Payment required",
        result.get("payment_required")
        is True,
    )

    check(
        "Payment not executed",
        result.get("payment_executed")
        is False,
    )

    check(
        "Order not created",
        result.get("order_created")
        is False,
    )

    check(
        "Checkout ready for payment",
        result.get("status")
        == "READY_FOR_PAYMENT",
    )


# ============================================================
# 6. INVALID QUANTITY
# ============================================================

def test_invalid_quantity():

    agent = CheckoutAgent()

    raised = False

    try:

        agent.create_checkout(

            customer_id=5176,

            product=PRODUCT,

            quantity=0,

            discount_percent=0,
        )

    except ValueError:

        raised = True

    check(
        "Zero quantity rejected",
        raised is True,
    )


# ============================================================
# 7. INVALID PRODUCT
# ============================================================

def test_invalid_product():

    agent = CheckoutAgent()

    raised = False

    try:

        agent.create_checkout(

            customer_id=5176,

            product={},

            quantity=1,

            discount_percent=0,
        )

    except ValueError:

        raised = True

    check(
        "Invalid product rejected",
        raised is True,
    )


# ============================================================
# 8. DISCOUNT BOUNDARY
# ============================================================

def test_discount_boundary():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=5176,

        product=PRODUCT,

        quantity=1,

        discount_percent=150,
    )

    check(
        "Discount capped at 100 percent",
        result.get("discount_percent")
        == 100.0,
    )

    check(
        "Final price cannot become negative",
        result.get("final_price")
        == 0.0,
    )


# ============================================================
# 9. UNKNOWN CUSTOMER
# ============================================================

def test_unknown_customer():

    agent = CheckoutAgent()

    result = agent.create_checkout(

        customer_id=None,

        product=PRODUCT,

        quantity=1,

        discount_percent=0,
    )

    check(
        "Anonymous checkout supported",
        isinstance(result, dict),
    )

    check(
        "Unknown customer remains anonymous",
        result.get("customer_id")
        is None,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global passed, failed

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS"
    )

    print(
        "PHASE 06A — CHECKOUT AGENT TEST SUITE"
    )

    print("=" * 80)

    print()

    test_basic_checkout()

    test_price_calculation()

    test_discount()

    test_quantity()

    test_payment_safety()

    test_invalid_quantity()

    test_invalid_product()

    test_discount_boundary()

    test_unknown_customer()

    print()

    print("=" * 80)

    print(
        "PHASE 06A CHECKOUT TEST SUMMARY"
    )

    print("=" * 80)

    total = passed + failed

    print(
        f"Total tests : {total}"
    )

    print(
        f"Passed      : {passed}"
    )

    print(
        f"Failed      : {failed}"
    )

    print()

    if failed == 0:

        print("=" * 80)

        print(
            "ALL PHASE 06A CHECKOUT TESTS PASSED"
        )

        print("=" * 80)

        return 0

    print("=" * 80)

    print(
        "PHASE 06A CHECKOUT TESTS FAILED"
    )

    print("=" * 80)

    return 1


if __name__ == "__main__":

    sys.exit(main())

