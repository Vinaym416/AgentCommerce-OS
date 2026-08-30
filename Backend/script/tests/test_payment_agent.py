
"""
AGENTCOMMERCE OS
PHASE 06B — PAYMENT AGENT TEST SUITE

Tests the simulated payment boundary.

IMPORTANT:
- No real payment is executed.
- No Razorpay API is called.
- Tests validate payment decision/state handling.
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(ROOT)
    )


from script.agents.payment_agent import (
    PaymentAgent,
    PaymentResult,
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
# TEST CONFIGURATION
# ============================================================

PRODUCT_ID = 453

PAYMENT_AMOUNT = 705.81


# ============================================================
# 1. BASIC SUCCESS
# ============================================================

def test_basic_payment():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="UPI",
    )

    check(
        "Payment returns PaymentResult",
        isinstance(
            result,
            PaymentResult,
        ),
    )

    check(
        "Payment succeeds",
        result.status
        == "PAYMENT_SUCCESS",
    )

    check(
        "Product ID preserved",
        result.product_id
        == PRODUCT_ID,
    )

    check(
        "Amount preserved",
        result.amount
        == PAYMENT_AMOUNT,
    )

    check(
        "Currency is INR",
        result.currency
        == "INR",
    )

    check(
        "Payment method preserved",
        result.payment_method
        == "UPI",
    )

    check(
        "Transaction ID generated",
        result.transaction_id
        is not None,
    )

    check(
        "Success reason generated",
        result.reason
        == "payment_processed_successfully",
    )


# ============================================================
# 2. PAYMENT METHOD NORMALIZATION
# ============================================================

def test_payment_method_normalization():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="upi",
    )

    check(
        "Lowercase payment method accepted",
        result.status
        == "PAYMENT_SUCCESS",
    )

    check(
        "Payment method normalized",
        result.payment_method
        == "UPI",
    )


# ============================================================
# 3. SUPPORTED PAYMENT METHODS
# ============================================================

def test_supported_payment_methods():

    agent = PaymentAgent()

    methods = [
        "UPI",
        "CARD",
        "NET_BANKING",
        "WALLET",
    ]

    for method in methods:

        result = agent.process_payment(

            product_id=PRODUCT_ID,

            amount=PAYMENT_AMOUNT,

            payment_method=method,
        )

        check(
            f"{method} payment method supported",
            result.status
            == "PAYMENT_SUCCESS",
            expected="PAYMENT_SUCCESS",
            actual=result.status,
        )


# ============================================================
# 4. INVALID AMOUNT
# ============================================================

def test_invalid_amount():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=0,

        payment_method="UPI",
    )

    check(
        "Zero amount rejected",
        result.status
        == "PAYMENT_FAILED",
    )

    check(
        "Invalid amount reason returned",
        result.reason
        == "invalid_amount",
    )

    check(
        "No transaction created",
        result.transaction_id
        is None,
    )


# ============================================================
# 5. NEGATIVE AMOUNT
# ============================================================

def test_negative_amount():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=-100,

        payment_method="UPI",
    )

    check(
        "Negative amount rejected",
        result.status
        == "PAYMENT_FAILED",
    )

    check(
        "Negative amount reason correct",
        result.reason
        == "invalid_amount",
    )

    check(
        "No transaction for negative amount",
        result.transaction_id
        is None,
    )


# ============================================================
# 6. UNSUPPORTED PAYMENT METHOD
# ============================================================

def test_unsupported_payment_method():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="CASH",
    )

    check(
        "Unsupported payment method rejected",
        result.status
        == "PAYMENT_FAILED",
    )

    check(
        "Unsupported method reason returned",
        result.reason
        == "unsupported_payment_method",
    )

    check(
        "No transaction created",
        result.transaction_id
        is None,
    )


# ============================================================
# 7. SIMULATED FAILURE
# ============================================================

def test_simulated_failure():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="UPI",

        simulate_failure=True,
    )

    check(
        "Simulated payment failure handled",
        result.status
        == "PAYMENT_FAILED",
    )

    check(
        "Failure reason returned",
        result.reason
        == "payment_declined",
    )

    check(
        "Failed payment has no transaction ID",
        result.transaction_id
        is None,
    )


# ============================================================
# 8. FAILED PAYMENT MUST NOT LOOK SUCCESSFUL
# ============================================================

def test_failure_safety():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="UPI",

        simulate_failure=True,
    )

    check(
        "Failed payment is not successful",
        result.status
        != "PAYMENT_SUCCESS",
    )

    check(
        "Failed payment has no transaction ID",
        result.transaction_id
        is None,
    )


# ============================================================
# 9. SUCCESSFUL PAYMENTS GET UNIQUE IDs
# ============================================================

def test_transaction_id_uniqueness():

    agent = PaymentAgent()

    result1 = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="UPI",
    )

    result2 = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="UPI",
    )

    check(
        "First transaction ID exists",
        result1.transaction_id
        is not None,
    )

    check(
        "Second transaction ID exists",
        result2.transaction_id
        is not None,
    )

    check(
        "Transaction IDs are unique",
        result1.transaction_id
        != result2.transaction_id,
    )


# ============================================================
# 10. AMOUNT ROUNDING
# ============================================================

def test_amount_rounding():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=705.8167,

        payment_method="UPI",
    )

    check(
        "Payment succeeds with decimal amount",
        result.status
        == "PAYMENT_SUCCESS",
    )

    check(
        "Amount rounded to two decimals",
        result.amount
        == 705.82,
        expected=705.82,
        actual=result.amount,
    )


# ============================================================
# 11. PAYMENT RESULT STRUCTURE
# ============================================================

def test_payment_result_structure():

    agent = PaymentAgent()

    result = agent.process_payment(

        product_id=PRODUCT_ID,

        amount=PAYMENT_AMOUNT,

        payment_method="CARD",
    )

    check(
        "Result has status",
        hasattr(
            result,
            "status",
        ),
    )

    check(
        "Result has product ID",
        hasattr(
            result,
            "product_id",
        ),
    )

    check(
        "Result has amount",
        hasattr(
            result,
            "amount",
        ),
    )

    check(
        "Result has currency",
        hasattr(
            result,
            "currency",
        ),
    )

    check(
        "Result has payment method",
        hasattr(
            result,
            "payment_method",
        ),
    )

    check(
        "Result has transaction ID",
        hasattr(
            result,
            "transaction_id",
        ),
    )

    check(
        "Result has reason",
        hasattr(
            result,
            "reason",
        ),
    )


# ============================================================
# 12. PRODUCT ID PRESERVATION
# ============================================================

def test_product_id_preservation():

    agent = PaymentAgent()

    product_ids = [
        1,
        453,
        999,
    ]

    for product_id in product_ids:

        result = agent.process_payment(

            product_id=product_id,

            amount=500,

            payment_method="UPI",
        )

        check(
            f"Product ID {product_id} preserved",
            result.product_id
            == product_id,
        )


# ============================================================
# 13. FAILURE DOES NOT GENERATE TRANSACTION
# ============================================================

def test_no_transaction_on_invalid_payment():

    agent = PaymentAgent()

    invalid_results = [

        agent.process_payment(
            product_id=PRODUCT_ID,
            amount=0,
            payment_method="UPI",
        ),

        agent.process_payment(
            product_id=PRODUCT_ID,
            amount=-50,
            payment_method="UPI",
        ),

        agent.process_payment(
            product_id=PRODUCT_ID,
            amount=PAYMENT_AMOUNT,
            payment_method="CASH",
        ),

        agent.process_payment(
            product_id=PRODUCT_ID,
            amount=PAYMENT_AMOUNT,
            payment_method="UPI",
            simulate_failure=True,
        ),
    ]

    for result in invalid_results:

        check(
            "Failed payment has no transaction ID",
            result.transaction_id
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
        "PHASE 06B — PAYMENT AGENT TEST SUITE"
    )

    print("=" * 80)

    print()

    test_basic_payment()

    test_payment_method_normalization()

    test_supported_payment_methods()

    test_invalid_amount()

    test_negative_amount()

    test_unsupported_payment_method()

    test_simulated_failure()

    test_failure_safety()

    test_transaction_id_uniqueness()

    test_amount_rounding()

    test_payment_result_structure()

    test_product_id_preservation()

    test_no_transaction_on_invalid_payment()

    print()

    print("=" * 80)

    print(
        "PHASE 06B PAYMENT TEST SUMMARY"
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
            "ALL PHASE 06B PAYMENT TESTS PASSED"
        )

        print("=" * 80)

        return 0

    print("=" * 80)

    print(
        "PHASE 06B PAYMENT TESTS FAILED"
    )

    print("=" * 80)

    return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )

