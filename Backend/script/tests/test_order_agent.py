
"""
AGENTCOMMERCE OS
PHASE 06C — ORDER AGENT TEST SUITE

Tests order creation after successful payment.

IMPORTANT:
- Payment execution is NOT performed here.
- Payment is represented by payment_status
  and payment_transaction_id.
- Failed payments must never create orders.
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from script.agents.order_agent import (
    OrderAgent,
    OrderResult,
)


# ============================================================
# TEST STATE
# ============================================================

passed = 0
failed = 0


# ============================================================
# CHECK HELPER
# ============================================================

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
# AGENT FACTORY
# ============================================================

def create_agent():

    return OrderAgent()


# ============================================================
# 1. SUCCESSFUL ORDER
# ============================================================

def test_successful_order():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-TEST-001",
    )

    check(
        "Order returns OrderResult",
        isinstance(result, OrderResult),
    )

    check(
        "Order created",
        result.status == "ORDER_CREATED",
    )

    check(
        "Order ID exists",
        result.order_id is not None,
    )

    check(
        "Order ID has correct prefix",
        result.order_id.startswith("ORD-"),
    )

    check(
        "Customer ID preserved",
        result.customer_id == 5176,
    )

    check(
        "Product ID preserved",
        result.product_id == 453,
    )

    check(
        "Amount preserved",
        result.amount == 705.81,
    )

    check(
        "Currency preserved",
        result.currency == "INR",
    )

    check(
        "Payment transaction ID preserved",
        result.payment_transaction_id
        == "TXN-TEST-001",
    )

    check(
        "Creation timestamp exists",
        bool(result.created_at),
    )

    check(
        "Success reason returned",
        result.reason
        == "order_created_after_successful_payment",
    )

    check(
        "Payment status is explicit",
        result.payment_status == "SUCCESS",
    )

    check(
        "Payment provider is Razorpay",
        result.payment_provider == "RAZORPAY",
    )

    check(
        "Confirmed order status is recorded",
        result.status == "CONFIRMED",
    )


# ============================================================
# 2. FAILED PAYMENT
# ============================================================

def test_failed_payment():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="FAILED",

        payment_transaction_id="TXN-FAILED-001",
    )

    check(
        "Failed payment does not create order",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "No order ID for failed payment",
        result.order_id is None,
    )

    check(
        "Correct failed payment reason",
        result.reason
        == "order_requires_successful_payment",
    )

    check(
        "Payment transaction preserved",
        result.payment_transaction_id
        == "TXN-FAILED-001",
    )


# ============================================================
# 3. ZERO AMOUNT
# ============================================================

def test_zero_amount():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=0,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-ZERO-001",
    )

    check(
        "Zero amount rejected",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "Zero amount reason returned",
        result.reason
        == "order_amount_must_be_positive",
    )

    check(
        "No order created for zero amount",
        result.order_id is None,
    )


# ============================================================
# 4. NEGATIVE AMOUNT
# ============================================================

def test_negative_amount():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=-100,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-NEGATIVE-001",
    )

    check(
        "Negative amount rejected",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "Negative amount reason correct",
        result.reason
        == "order_amount_must_be_positive",
    )

    check(
        "No order created for negative amount",
        result.order_id is None,
    )


# ============================================================
# 5. MISSING CUSTOMER
# ============================================================

def test_missing_customer():

    agent = create_agent()

    result = agent.create_order(

        customer_id=None,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-CUSTOMER-001",
    )

    check(
        "Missing customer rejected",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "Customer validation reason returned",
        result.reason
        == "customer_id_required",
    )

    check(
        "No order created",
        result.order_id is None,
    )


# ============================================================
# 6. MISSING PRODUCT
# ============================================================

def test_missing_product():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=None,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-PRODUCT-001",
    )

    check(
        "Missing product rejected",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "Product validation reason returned",
        result.reason
        == "product_id_required",
    )

    check(
        "No order created",
        result.order_id is None,
    )


# ============================================================
# 7. SUCCESS WITHOUT TRANSACTION ID
# ============================================================

def test_missing_transaction_id():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id=None,
    )

    check(
        "Success without transaction rejected",
        result.status == "ORDER_NOT_CREATED",
    )

    check(
        "Transaction ID validation reason returned",
        result.reason
        == "payment_transaction_id_required",
    )

    check(
        "No order created",
        result.order_id is None,
    )


# ============================================================
# 8. TRANSACTION IDS UNIQUE
# ============================================================

def test_unique_order_ids():

    agent = create_agent()

    result1 = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        payment_status="SUCCESS",

        payment_transaction_id="TXN-UNIQUE-001",
    )

    result2 = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        payment_status="SUCCESS",

        payment_transaction_id="TXN-UNIQUE-002",
    )

    check(
        "First order ID exists",
        result1.order_id is not None,
    )

    check(
        "Second order ID exists",
        result2.order_id is not None,
    )

    check(
        "Order IDs are unique",
        result1.order_id != result2.order_id,
    )


# ============================================================
# 9. DECIMAL AMOUNT
# ============================================================

def test_decimal_amount():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.8167,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-DECIMAL-001",
    )

    check(
        "Decimal order succeeds",
        result.status == "ORDER_CREATED",
    )

    check(
        "Amount rounded to two decimals",
        result.amount == 705.82,
        expected=705.82,
        actual=result.amount,
    )


# ============================================================
# 10. CURRENCY NORMALIZATION
# ============================================================

def test_currency_normalization():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="inr",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-CURRENCY-001",
    )

    check(
        "Lowercase currency accepted",
        result.status == "ORDER_CREATED",
    )

    check(
        "Currency normalized",
        result.currency == "INR",
    )


# ============================================================
# 11. FAILED PAYMENT HAS NO ORDER
# ============================================================

def test_failed_payment_safety():

    agent = create_agent()

    payment_statuses = [
        "FAILED",
        "DECLINED",
        "CANCELLED",
        "PENDING",
    ]

    for status in payment_statuses:

        result = agent.create_order(

            customer_id=5176,

            product_id=453,

            amount=705.81,

            currency="INR",

            payment_status=status,

            payment_transaction_id=(
                f"TXN-{status}"
            ),
        )

        check(
            f"{status} payment cannot create order",
            result.order_id is None,
        )

        check(
            f"{status} payment returns safe status",
            result.status == "ORDER_NOT_CREATED",
        )


# ============================================================
# 12. RESULT STRUCTURE
# ============================================================

def test_result_structure():

    agent = create_agent()

    result = agent.create_order(

        customer_id=5176,

        product_id=453,

        amount=705.81,

        currency="INR",

        payment_status="SUCCESS",

        payment_transaction_id="TXN-STRUCTURE-001",
    )

    check(
        "Result has status",
        hasattr(result, "status"),
    )

    check(
        "Result has order ID",
        hasattr(result, "order_id"),
    )

    check(
        "Result has customer ID",
        hasattr(result, "customer_id"),
    )

    check(
        "Result has product ID",
        hasattr(result, "product_id"),
    )

    check(
        "Result has amount",
        hasattr(result, "amount"),
    )

    check(
        "Result has currency",
        hasattr(result, "currency"),
    )

    check(
        "Result has payment transaction ID",
        hasattr(
            result,
            "payment_transaction_id",
        ),
    )

    check(
        "Result has creation timestamp",
        hasattr(result, "created_at"),
    )

    check(
        "Result has reason",
        hasattr(result, "reason"),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS"
    )

    print(
        "PHASE 06C — ORDER AGENT TEST SUITE"
    )

    print("=" * 80)

    print()

    test_successful_order()

    test_failed_payment()

    test_zero_amount()

    test_negative_amount()

    test_missing_customer()

    test_missing_product()

    test_missing_transaction_id()

    test_unique_order_ids()

    test_decimal_amount()

    test_currency_normalization()

    test_failed_payment_safety()

    test_result_structure()

    print()

    print("=" * 80)

    print(
        "PHASE 06C ORDER TEST SUMMARY"
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
            "ALL PHASE 06C ORDER TESTS PASSED"
        )

        print("=" * 80)

        return 0

    print("=" * 80)

    print(
        "PHASE 06C ORDER TESTS FAILED"
    )

    print("=" * 80)

    return 1


if __name__ == "__main__":

    sys.exit(main())

