
"""
AGENTCOMMERCE OS
PHASE 06D — COMMERCE EXECUTION AGENT TEST SUITE

Tests the execution boundary:

Checkout
   ↓
Payment
   ↓
Order

The Commerce Execution Agent is responsible for executing
an already-approved commerce decision.

It does NOT perform product recommendation,
negotiation, merchant decision, or policy evaluation.
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORT
# ============================================================

from script.agents.commerce_execution_agent import (
    CommerceExecutionAgent
)


# ============================================================
# TEST HELPERS
# ============================================================

total_tests = 0
passed_tests = 0


def check(condition, message):
    global total_tests
    global passed_tests

    total_tests += 1

    if condition:
        passed_tests += 1
        print(f"[PASS] {message}")
    else:
        print(f"[FAIL] {message}")


# ============================================================
# TEST 1 — CHECKOUT ONLY
# ============================================================

def test_checkout_only():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=False
    )

    check(
        isinstance(result, dict),
        "Checkout returns dictionary"
    )

    check(
        result["checkout"] is not None,
        "Checkout result exists"
    )

    check(
        result["checkout"]["status"] == "CHECKOUT_READY",
        "Checkout is ready"
    )

    check(
        result["checkout"]["final_price"] == 705.81,
        "Checkout final price calculated correctly"
    )

    check(
        result["payment"] is None,
        "Payment not executed"
    )

    check(
        result["order"] is None,
        "Order not created"
    )

    check(
        result["final_action"] == "CHECKOUT_READY",
        "Final action is CHECKOUT_READY"
    )


# ============================================================
# TEST 2 — SUCCESSFUL PAYMENT
# ============================================================

def test_successful_payment():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=True
    )

    check(
        result["checkout"]["status"] == "CHECKOUT_READY",
        "Checkout ready before payment"
    )

    check(
        result["payment"] is not None,
        "Payment result exists"
    )

    check(
        result["payment"]["status"] == "PAYMENT_SUCCESS",
        "Payment succeeds"
    )

    check(
        result["payment"]["transaction_id"] is not None,
        "Payment transaction ID exists"
    )

    check(
        result["order"] is not None,
        "Order result exists"
    )

    check(
        result["order"]["status"] == "ORDER_CREATED",
        "Order created after successful payment"
    )

    check(
        result["order"]["payment_transaction_id"]
        == result["payment"]["transaction_id"],
        "Order linked to payment transaction"
    )

    check(
        result["order"]["amount"]
        == result["payment"]["amount"],
        "Order amount matches payment amount"
    )

    check(
        result["final_action"] == "ORDER_CREATED",
        "Final action is ORDER_CREATED"
    )


# ============================================================
# TEST 3 — PAYMENT FAILURE
# ============================================================

def test_payment_failure():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=True,
        simulate_failure=True
    )

    check(
        result["checkout"]["status"] == "CHECKOUT_READY",
        "Checkout succeeds before failed payment"
    )

    check(
        result["payment"] is not None,
        "Payment failure result exists"
    )

    check(
        result["payment"]["status"] == "PAYMENT_FAILED",
        "Payment failure handled"
    )

    check(
        result["payment"]["transaction_id"] is None,
        "Failed payment has no transaction ID"
    )

    check(
        result["order"] is None,
        "Order not created after failed payment"
    )

    check(
        result["final_action"] == "PAYMENT_FAILED",
        "Final action is PAYMENT_FAILED"
    )


# ============================================================
# TEST 4 — INVALID PRICE
# ============================================================

def test_invalid_price():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=0,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=True
    )

    check(
        result["checkout"] is None,
        "Invalid price prevents checkout"
    )

    check(
        result["payment"] is None,
        "Invalid price prevents payment"
    )

    check(
        result["order"] is None,
        "Invalid price prevents order"
    )

    check(
        result["final_action"] == "EXECUTION_FAILED",
        "Invalid price returns EXECUTION_FAILED"
    )

    check(
        result["reason"] == "product_price_must_be_positive",
        "Correct invalid price reason returned"
    )


# ============================================================
# TEST 5 — UNSUPPORTED PAYMENT METHOD
# ============================================================

def test_unsupported_payment_method():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="CASH",
        execute_payment=True
    )

    check(
        result["checkout"] is not None,
        "Checkout still succeeds"
    )

    check(
        result["payment"] is not None,
        "Payment result exists"
    )

    check(
        result["payment"]["status"] == "PAYMENT_FAILED",
        "Unsupported payment method rejected"
    )

    check(
        result["payment"]["reason"]
        == "unsupported_payment_method",
        "Correct unsupported payment reason returned"
    )

    check(
        result["order"] is None,
        "Order not created after unsupported payment"
    )

    check(
        result["final_action"] == "PAYMENT_FAILED",
        "Final action is PAYMENT_FAILED"
    )


# ============================================================
# TEST 6 — NO CUSTOMER
# ============================================================

def test_anonymous_execution():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=None,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=True
    )

    check(
        result["customer"]["customer_id"] is None,
        "Anonymous customer supported"
    )

    check(
        result["customer"]["known_customer"] is False,
        "Anonymous customer marked correctly"
    )

    check(
        result["checkout"] is not None,
        "Anonymous checkout succeeds"
    )

    check(
        result["payment"]["status"] == "PAYMENT_SUCCESS",
        "Anonymous payment succeeds"
    )

    check(
        result["order"] is None,
        "Order not created without customer ID"
    )


# ============================================================
# TEST 7 — ZERO DISCOUNT
# ============================================================

def test_zero_discount():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=0,
        payment_method="UPI",
        execute_payment=True
    )

    check(
        result["checkout"]["discount_percent"] == 0,
        "Zero discount preserved"
    )

    check(
        result["checkout"]["final_price"] == 784.23,
        "Zero discount preserves original price"
    )

    check(
        result["payment"]["amount"] == 784.23,
        "Payment uses final checkout price"
    )

    check(
        result["order"]["amount"] == 784.23,
        "Order uses final checkout price"
    )


# ============================================================
# TEST 8 — DISCOUNT FLOW
# ============================================================

def test_discount_flow():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=1000,
        discount_percent=20,
        payment_method="UPI",
        execute_payment=True
    )

    check(
        result["checkout"]["original_price"] == 1000,
        "Original price preserved"
    )

    check(
        result["checkout"]["discount_percent"] == 20,
        "Discount percentage preserved"
    )

    check(
        result["checkout"]["discount_amount"] == 200,
        "Discount amount calculated"
    )

    check(
        result["checkout"]["final_price"] == 800,
        "Final checkout price calculated"
    )

    check(
        result["payment"]["amount"] == 800,
        "Payment uses discounted price"
    )

    check(
        result["order"]["amount"] == 800,
        "Order uses discounted price"
    )


# ============================================================
# TEST 9 — EXECUTION TRACE
# ============================================================

def test_execution_trace():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=True
    )

    trace = result["agent_trace"]

    check(
        "CHECKOUT" in trace,
        "Execution trace contains CHECKOUT"
    )

    check(
        "CHECKOUT_READY" in trace,
        "Execution trace contains CHECKOUT_READY"
    )

    check(
        "PAYMENT" in trace,
        "Execution trace contains PAYMENT"
    )

    check(
        "PAYMENT_SUCCESS" in trace,
        "Execution trace contains PAYMENT_SUCCESS"
    )

    check(
        "ORDER" in trace,
        "Execution trace contains ORDER"
    )

    check(
        "ORDER_CREATED" in trace,
        "Execution trace contains ORDER_CREATED"
    )

    check(
        "EXECUTION_COMPLETE" in trace,
        "Execution trace contains EXECUTION_COMPLETE"
    )


# ============================================================
# TEST 10 — PAYMENT → ORDER LINK
# ============================================================

def test_payment_order_link():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="CARD",
        execute_payment=True
    )

    payment = result["payment"]
    order = result["order"]

    check(
        payment is not None,
        "Payment exists"
    )

    check(
        order is not None,
        "Order exists"
    )

    check(
        payment["transaction_id"]
        == order["payment_transaction_id"],
        "Payment transaction linked to order"
    )

    check(
        payment["product_id"]
        == order["product_id"],
        "Payment product linked to order"
    )

    check(
        payment["currency"]
        == order["currency"],
        "Payment currency linked to order"
    )


# ============================================================
# TEST 11 — PAYMENT NOT EXECUTED
# ============================================================

def test_payment_not_executed():

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        payment_method="UPI",
        execute_payment=False
    )

    check(
        result["payment"] is None,
        "Payment remains unexecuted"
    )

    check(
        result["order"] is None,
        "Order remains uncreated"
    )

    check(
        result["final_action"] == "CHECKOUT_READY",
        "Execution stops at checkout"
    )

    check(
        "PAYMENT_NOT_EXECUTED"
        in result["agent_trace"],
        "Trace records payment not executed"
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 06D — COMMERCE EXECUTION AGENT TEST SUITE")
    print("=" * 80)

    print()

    test_checkout_only()
    test_successful_payment()
    test_payment_failure()
    test_invalid_price()
    test_unsupported_payment_method()
    test_anonymous_execution()
    test_zero_discount()
    test_discount_flow()
    test_execution_trace()
    test_payment_order_link()
    test_payment_not_executed()

    print()
    print("=" * 80)
    print("PHASE 06D EXECUTION TEST SUMMARY")
    print("=" * 80)

    print(f"Total tests : {total_tests}")
    print(f"Passed      : {passed_tests}")
    print(f"Failed      : {total_tests - passed_tests}")

    print()

    if total_tests == passed_tests:
        print("=" * 80)
        print("ALL PHASE 06D COMMERCE EXECUTION TESTS PASSED")
        print("=" * 80)
    else:
        print("=" * 80)
        print("SOME PHASE 06D TESTS FAILED")
        print("=" * 80)

        raise SystemExit(1)


if __name__ == "__main__":
    main()

