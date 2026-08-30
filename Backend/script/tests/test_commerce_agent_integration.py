
"""
AGENTCOMMERCE OS
PHASE 07 — COMMERCE AGENT INTEGRATION TEST SUITE

Tests the complete customer-aware commerce flow:

Customer
   ↓
Commerce Agent
   ↓
Customer Context
   ↓
Buyer Agent
   ↓
Product Retriever
   ↓
Opportunity Engine
   ↓
Merchant Decision Engine
   ↓
Negotiation Agent
   ↓
Policy Engine
   ↓
Commerce Execution
   ↓
Checkout
   ↓
Payment
   ↓
Order
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

from script.agents.commerce_agent import CommerceAgent


# ============================================================
# TEST CONFIGURATION
# ============================================================

CUSTOMER_ID = 5176


# ============================================================
# TEST HELPERS
# ============================================================

total_tests = 0
passed_tests = 0


def check(condition, message):
    global total_tests, passed_tests

    total_tests += 1

    if condition:
        passed_tests += 1
        print(f"[PASS] {message}")
    else:
        print(f"[FAIL] {message}")


def section(title):
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


# ============================================================
# TEST 1
# BASIC CUSTOMER-AWARE RECOMMENDATION
# ============================================================

def test_customer_recommendation():

    section("TEST 1 — CUSTOMER-AWARE PRODUCT RECOMMENDATION")

    agent = CommerceAgent()

    result = agent.process(
        message="I want a product under ₹2000.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        isinstance(result, dict),
        "Commerce Agent returns dictionary"
    )

    check(
        "customer" in result,
        "Customer section exists"
    )

    check(
        result["customer"]["customer_id"] == CUSTOMER_ID,
        "Customer ID preserved"
    )

    check(
        result["customer"]["known_customer"] is True,
        "Known customer detected"
    )

    check(
        "customer_intent" in result,
        "Customer intent exists"
    )

    check(
        result["customer_intent"]["intent"] is not None,
        "Customer intent detected"
    )

    check(
        "products" in result,
        "Products section exists"
    )

    check(
        len(result["products"]) > 0,
        "At least one product retrieved"
    )

    check(
        "intelligence" in result,
        "Opportunity intelligence exists"
    )

    check(
        "purchase_opportunity_score"
        in result["intelligence"],
        "Purchase opportunity score exists"
    )

    check(
        "merchant_decision" in result,
        "Merchant decision section exists"
    )

    check(
        result["final_action"] is not None,
        "Final commerce decision exists"
    )


# ============================================================
# TEST 2
# DISCOUNT REQUEST
# ============================================================

def test_discount_negotiation():

    section("TEST 2 — DISCOUNT NEGOTIATION + POLICY")

    agent = CommerceAgent()

    result = agent.process(
        message="I like this product but can you give me 10% off?",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        isinstance(result, dict),
        "Discount request returns dictionary"
    )

    check(
        result["customer"]["customer_id"] == CUSTOMER_ID,
        "Customer preserved during negotiation"
    )

    check(
        result["customer_intent"]["discount_requested"] is True,
        "Discount request detected"
    )

    check(
        "negotiation" in result,
        "Negotiation result exists"
    )

    check(
        result["negotiation"] is not None,
        "Negotiation was performed"
    )

    check(
        "policy" in result,
        "Policy result exists"
    )

    check(
        result["policy"] is not None,
        "Discount policy evaluated"
    )

    check(
        result["final_action"] in {
            "OFFER_REQUESTED",
            "COUNTER_OFFER",
            "NEGOTIATE",
            "RECOMMEND_PRODUCT",
        },
        "Final action is a valid commercial action"
    )


# ============================================================
# TEST 3
# OFFER CREATION
# ============================================================

def test_offer_creation():

    section("TEST 3 — OFFER / TRANSACTION CREATION")

    agent = CommerceAgent()

    result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        result["products"],
        "Product exists for offer"
    )

    check(
        result["policy"] is not None,
        "Policy evaluated for offer"
    )

    if result["final_action"] in {
        "OFFER_REQUESTED",
        "COUNTER_OFFER",
    }:

        check(
            result["final_action"] in {
                "OFFER_REQUESTED",
                "COUNTER_OFFER",
            },
            "Offer action created"
        )

    else:

        check(
            result["final_action"] == "RECOMMEND_PRODUCT",
            "Offer safely resolved as recommendation"
        )


# ============================================================
# TEST 4
# CUSTOMER ACCEPTANCE
# ============================================================

def test_customer_acceptance():

    section("TEST 4 — CUSTOMER ACCEPTANCE → CHECKOUT")

    agent = CommerceAgent()

    # First create an offer.
    first_result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        isinstance(first_result, dict),
        "Initial offer request processed"
    )

    # Customer accepts the pending offer.
    result = agent.process(
        message="Yes, I'll take it.",
        customer_id=CUSTOMER_ID,
        payment_method="UPI",
        execute_payment=False,
    )

    check(
        isinstance(result, dict),
        "Acceptance returns dictionary"
    )

    check(
        result.get("checkout") is not None,
        "Checkout result exists after acceptance"
    )

    if result.get("checkout"):

        check(
            result["checkout"]["status"] == "CHECKOUT_READY",
            "Checkout is ready"
        )

        check(
            result["checkout"]["payment_ready"] is True,
            "Checkout is payment-ready"
        )

        check(
            result["checkout"]["final_price"] > 0,
            "Checkout final price is positive"
        )

    check(
        result.get("payment") is None,
        "Payment is not executed when execute_payment=False"
    )

    check(
        result.get("order") is None,
        "Order is not created before payment"
    )


# ============================================================
# TEST 5
# FULL EXECUTION
# ============================================================

def test_full_execution():

    section("TEST 5 — FULL CHECKOUT → PAYMENT → ORDER")

    agent = CommerceAgent()

    # Create an offer first.
    offer_result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        isinstance(offer_result, dict),
        "Offer request processed"
    )

    # Accept and execute payment.
    result = agent.process(
        message="Yes, I'll take it.",
        customer_id=CUSTOMER_ID,
        payment_method="UPI",
        execute_payment=True,
    )

    check(
        result.get("checkout") is not None,
        "Checkout exists"
    )

    check(
        result["checkout"]["status"] == "CHECKOUT_READY",
        "Checkout ready before payment"
    )

    check(
        result.get("payment") is not None,
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
        result.get("order") is not None,
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
        result["order"]["product_id"]
        == result["payment"]["product_id"],
        "Order product matches payment product"
    )

    check(
        result["final_action"] == "ORDER_CREATED",
        "Final action is ORDER_CREATED"
    )


# ============================================================
# TEST 6
# PAYMENT FAILURE
# ============================================================

def test_payment_failure():

    section("TEST 6 — PAYMENT FAILURE PROPAGATION")

    agent = CommerceAgent()

    # Create offer.
    offer_result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    check(
        isinstance(offer_result, dict),
        "Offer created before payment failure test"
    )

    # Accept but simulate failed payment.
    result = agent.process(
        message="Yes, I'll take it.",
        customer_id=CUSTOMER_ID,
        payment_method="UPI",
        execute_payment=True,
        simulate_failure=True,
    )

    check(
        result.get("checkout") is not None,
        "Checkout succeeds before payment"
    )

    check(
        result.get("payment") is not None,
        "Payment failure result exists"
    )

    check(
        result["payment"]["status"] == "PAYMENT_FAILED",
        "Payment failure propagated"
    )

    check(
        result["payment"]["transaction_id"] is None,
        "Failed payment has no transaction ID"
    )

    check(
        result.get("order") is None,
        "Order is not created after failed payment"
    )

    check(
        result["final_action"] == "PAYMENT_FAILED",
        "Final action is PAYMENT_FAILED"
    )


# ============================================================
# TEST 7
# ANONYMOUS CUSTOMER
# ============================================================

def test_anonymous_customer():

    section("TEST 7 — ANONYMOUS CUSTOMER FLOW")

    agent = CommerceAgent()

    result = agent.process(
        message="I want a product under ₹2000.",
        customer_id=None,
        execute_payment=False,
    )

    check(
        isinstance(result, dict),
        "Anonymous request returns dictionary"
    )

    check(
        result["customer"]["customer_id"] is None,
        "Anonymous customer has no customer ID"
    )

    check(
        result["customer"]["known_customer"] is False,
        "Anonymous customer marked correctly"
    )

    check(
        len(result["products"]) > 0,
        "Anonymous customer can retrieve products"
    )


# ============================================================
# TEST 8
# EMPTY MESSAGE
# ============================================================

def test_empty_message():

    section("TEST 8 — INVALID CUSTOMER MESSAGE")

    agent = CommerceAgent()

    try:

        agent.process(
            message="",
            customer_id=CUSTOMER_ID,
        )

        check(
            False,
            "Empty message rejected"
        )

    except ValueError as exc:

        check(
            str(exc) == "Customer message cannot be empty.",
            "Correct empty-message validation"
        )


# ============================================================
# TEST 9
# TRACE VALIDATION
# ============================================================

def test_agent_trace():

    section("TEST 9 — AGENT ORCHESTRATION TRACE")

    agent = CommerceAgent()

    result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    trace = result.get("agent_trace", [])

    check(
        "CUSTOMER_CONTEXT" in trace,
        "Trace contains CUSTOMER_CONTEXT"
    )

    check(
        "BUYER_AGENT" in trace,
        "Trace contains BUYER_AGENT"
    )

    check(
        "PRODUCT_RETRIEVER" in trace
        or "AGENT_MEMORY" in trace,
        "Trace contains product resolution"
    )

    check(
        "OPPORTUNITY_ENGINE" in trace,
        "Trace contains OPPORTUNITY_ENGINE"
    )

    check(
        "MERCHANT_DECISION_ENGINE" in trace,
        "Trace contains MERCHANT_DECISION_ENGINE"
    )

    check(
        "NEGOTIATION_AGENT" in trace,
        "Trace contains NEGOTIATION_AGENT"
    )

    check(
        "POLICY_ENGINE" in trace,
        "Trace contains POLICY_ENGINE"
    )

    check(
        "FINAL_DECISION" in trace,
        "Trace contains FINAL_DECISION"
    )


# ============================================================
# TEST 10
# DISCOUNT PRICE CONSISTENCY
# ============================================================

def test_price_consistency():

    section("TEST 10 — COMMERCIAL PRICE CONSISTENCY")

    agent = CommerceAgent()

    result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    products = result.get("products", [])
    policy = result.get("policy")

    check(
        len(products) > 0,
        "Product exists"
    )

    if products and policy:

        original_price = products[0]["price"]

        approved_discount = float(
            policy.get(
                "approved_discount",
                0
            )
        )

        final_price = float(
            policy.get(
                "final_price",
                original_price
            )
        )

        expected_price = round(
            original_price
            * (1 - approved_discount / 100),
            2
        )

        check(
            final_price == expected_price,
            "Policy final price matches approved discount"
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():

    global total_tests
    global passed_tests

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 07 — COMMERCE AGENT INTEGRATION TEST SUITE")
    print("=" * 80)

    tests = [
        test_customer_recommendation,
        test_discount_negotiation,
        test_offer_creation,
        test_customer_acceptance,
        test_full_execution,
        test_payment_failure,
        test_anonymous_customer,
        test_empty_message,
        test_agent_trace,
        test_price_consistency,
    ]

    for test in tests:

        try:

            test()

        except Exception as exc:

            total_tests += 1

            print(
                f"[FAIL] {test.__name__} "
                f"raised {type(exc).__name__}: {exc}"
            )

    print("\n" + "=" * 80)
    print("PHASE 07 INTEGRATION TEST SUMMARY")
    print("=" * 80)

    print(
        f"Total tests : {total_tests}"
    )

    print(
        f"Passed      : {passed_tests}"
    )

    print(
        f"Failed      : "
        f"{total_tests - passed_tests}"
    )

    print("=" * 80)

    if total_tests == passed_tests:

        print(
            "ALL PHASE 07 COMMERCE INTEGRATION TESTS PASSED"
        )

    else:

        print(
            "PHASE 07 INTEGRATION TESTS HAVE FAILURES"
        )

    print("=" * 80)


if __name__ == "__main__":
    main()

