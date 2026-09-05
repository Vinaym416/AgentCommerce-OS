
"""
AGENTCOMMERCE OS
PHASE 05 — CUSTOMER-AWARE COMMERCE AGENT TEST SUITE

Tests the complete customer-aware commerce pipeline:

Customer
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
Safe Commerce Decision

IMPORTANT:
- Payment execution is DISABLED in this test suite.
- Tests validate the orchestration layer.
- Payment/order execution is tested separately.
"""

import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from script.agents.commerce_agent import CommerceAgent


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
        print(f"[PASS] {test_name}")

    else:
        failed += 1
        print(f"[FAIL] {test_name}")

        if expected is not None:
            print(f"       Expected: {expected}")

        if actual is not None:
            print(f"       Actual:   {actual}")


# ============================================================
# TEST CONFIGURATION
# ============================================================

CUSTOMER_ID = 5176


# ============================================================
# AGENT FACTORY
# ============================================================

def create_agent():

    return CommerceAgent()


# ============================================================
# SAFE PROCESS HELPER
# ============================================================

def process(
    agent,
    message,
    customer_id=CUSTOMER_ID,
):
    """
    Centralized test invocation.

    Payment execution is intentionally disabled.
    """

    return agent.process(
        message=message,
        customer_id=customer_id,
        payment_method="UPI",
        execute_payment=False,
        simulate_failure=False,
    )


def test_missing_shopping_context_is_requested_before_buyer_agent():
    agent = create_agent()

    def buyer_agent_should_not_run(_message):
        raise AssertionError("BuyerAgent must not run before context is complete")

    agent.buyer_agent.extract_intent = buyer_agent_should_not_run

    result = process(agent, "Find me running shoes")

    assert result["action"] == "CONTEXT_REQUIRED"
    assert result["customer_intent"]["missing_context"] == [
        "budget",
        "urgency",
    ]


def test_budget_and_urgency_are_detected_from_customer_message():
    agent = create_agent()

    assert CommerceAgent._has_explicit_budget("running shoes under ₹3000")
    assert CommerceAgent._has_explicit_urgency("I need them urgently")
    assert CommerceAgent._has_explicit_category("running shoes")
    assert agent._missing_shopping_context(
        "Find running shoes under ₹3000 urgently",
        product_id=None,
        button_action=None,
    ) == []


# ============================================================
# 1. BASIC CUSTOMER-AWARE REQUEST
# ============================================================

def test_product_selection_resets_on_new_search():
    from script.context.agent_memory import AgentMemory

    memory = AgentMemory()
    memory.set_customer(5176)

    class DummyProduct:
        product_id = 101

    memory.set_products([DummyProduct(), DummyProduct()], customer_id=5176)
    assert memory.get_selected_product(5176).product_id == 101

    memory.reset_product_selection(customer_id=5176)
    assert memory.get_selected_product(5176) is None


def test_explicit_product_selection_bypasses_full_list_recommendation():
    from types import SimpleNamespace

    agent = create_agent()
    agent.memory.set_customer(CUSTOMER_ID)
    agent.memory.set_products(
        [
            SimpleNamespace(product_id=100, product_name="Alpha", category_name="Phone", availability=True, currency="INR", current_price=1000, rating=4.0, conversion_rate=1.0, demand_score=1.0, quality_score=1.0, product_score=1.0),
            SimpleNamespace(product_id=200, product_name="Beta", category_name="Phone", availability=True, currency="INR", current_price=2000, rating=4.0, conversion_rate=1.0, demand_score=1.0, quality_score=1.0, product_score=1.0),
        ],
        customer_id=CUSTOMER_ID,
    )

    result = agent.process(
        message="I want product 200.",
        customer_id=CUSTOMER_ID,
        product_id=200,
    )

    assert result["products"][0]["product_id"] == 200
    assert len(result["products"]) == 1


def test_basic_request():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    check(
        "Basic request returns result",
        isinstance(result, dict),
    )

    check(
        "Customer information exists",
        "customer" in result,
    )

    check(
        "Customer context exists",
        "customer_context" in result,
    )

    check(
        "Customer intent exists",
        "customer_intent" in result,
    )

    check(
        "Products field exists",
        "products" in result,
    )

    check(
        "Final action exists",
        "final_action" in result,
    )


# ============================================================
# 2. CUSTOMER CONTEXT
# ============================================================

def test_customer_context():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    customer = result.get(
        "customer",
        {},
    )

    context = result.get(
        "customer_context"
    )

    check(
        "Customer ID preserved",
        customer.get("customer_id")
        == CUSTOMER_ID,
        expected=CUSTOMER_ID,
        actual=customer.get("customer_id"),
    )

    check(
        "Known customer detected",
        customer.get("known_customer") is True,
    )

    check(
        "Customer context loaded",
        context is not None,
    )

    if context is not None:

        check(
            "Customer sessions available",
            "sessions" in context,
        )

        check(
            "Customer purchase rate available",
            "purchase_rate" in context,
        )

        check(
            "Customer affinity available",
            "customer_affinity_score" in context,
        )


# ============================================================
# 3. BUYER AGENT
# ============================================================

def test_buyer_agent():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    intent = result.get(
        "customer_intent",
        {},
    )

    check(
        "Buyer intent generated",
        bool(intent),
    )

    check(
        "Budget extracted",
        intent.get("budget") == 2000,
        expected=2000,
        actual=intent.get("budget"),
    )

    check(
        "Intent field exists",
        "intent" in intent,
    )

    check(
        "Urgency field exists",
        "urgency" in intent,
    )

    check(
        "Discount request field exists",
        "discount_requested" in intent,
    )

    check(
        "Confidence field exists",
        "confidence" in intent,
    )


def test_price_followup_does_not_match_office():

    agent = create_agent()

    check(
        "Office is not a discount request",
        agent._is_price_followup(
            "Looking for a minimalist black bag for daily office commuting."
        ) is False,
    )

    check(
        "Discount phrase is detected",
        agent._is_price_followup("Can you give me 10% off?") is True,
    )


# ============================================================
# 4. PRODUCT RETRIEVAL
# ============================================================

def test_product_retrieval():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    products = result.get(
        "products",
        [],
    )

    check(
        "Product list returned",
        isinstance(products, list),
    )

    check(
        "At least one product returned",
        len(products) > 0,
    )

    if products:

        product = products[0]

        check(
            "Product has product_id",
            "product_id" in product,
        )

        check(
            "Product has price",
            "price" in product,
        )

        check(
            "Product has rating",
            "rating" in product,
        )

        check(
            "Product has product score",
            "product_score" in product,
        )


# ============================================================
# 5. OPPORTUNITY ENGINE
# ============================================================

def test_opportunity_engine():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    intelligence = result.get(
        "intelligence",
        {},
    )

    check(
        "Intelligence result generated",
        isinstance(intelligence, dict),
    )

    check(
        "Purchase opportunity score exists",
        "purchase_opportunity_score"
        in intelligence,
    )

    check(
        "Discount opportunity score exists",
        "discount_opportunity_score"
        in intelligence,
    )

    if intelligence:

        purchase_score = intelligence.get(
            "purchase_opportunity_score"
        )

        discount_score = intelligence.get(
            "discount_opportunity_score"
        )

        check(
            "Purchase score is numeric",
            isinstance(
                purchase_score,
                (int, float),
            ),
        )

        check(
            "Discount score is numeric",
            isinstance(
                discount_score,
                (int, float),
            ),
        )


# ============================================================
# 6. MERCHANT DECISION
# ============================================================

def test_merchant_decision():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    decision = result.get(
        "merchant_decision"
    )

    check(
        "Merchant decision generated",
        decision is not None,
    )

    if decision:

        check(
            "Merchant action exists",
            "action" in decision,
        )

        check(
            "Approved discount exists",
            "approved_discount" in decision,
        )

        check(
            "Negotiation permission exists",
            "negotiation_allowed" in decision,
        )

        check(
            "Approval status exists",
            "approval_status" in decision,
        )


# ============================================================
# 7. NEGOTIATION
# ============================================================

def test_negotiation():

    agent = create_agent()

    result = process(
        agent,
        "I like this product but can you give me 10% off?",
    )

    intent = result.get(
        "customer_intent",
        {},
    )

    negotiation = result.get(
        "negotiation"
    )

    check(
        "Discount request detected",
        intent.get("discount_requested")
        is True,
    )

    check(
        "Negotiation result generated",
        negotiation is not None,
    )

    if negotiation:

        check(
            "Negotiation action exists",
            "action" in negotiation,
        )

        check(
            "Requested discount exists",
            "requested_discount"
            in negotiation,
        )

        check(
            "Offered discount exists",
            "offered_discount"
            in negotiation,
        )

        check(
            "Counter-offer field exists",
            "counter_offer"
            in negotiation,
        )


# ============================================================
# 8. POLICY ENGINE
# ============================================================

def test_policy():

    agent = create_agent()

    result = process(
        agent,
        "I like this product but can you give me 10% off?",
    )

    policy = result.get(
        "policy"
    )

    check(
        "Policy result generated",
        policy is not None,
    )

    if policy:

        check(
            "Policy allowed field exists",
            "allowed" in policy,
        )

        check(
            "Policy approved discount exists",
            "approved_discount" in policy,
        )

        check(
            "Policy final price exists",
            "final_price" in policy,
        )

        check(
            "Policy reasons exist",
            "reasons" in policy,
        )


# ============================================================
# 9. FINAL COMMERCE DECISION
# ============================================================

def test_final_decision():

    agent = create_agent()

    result = process(
        agent,
        "I like this product but can you give me 10% off?",
    )

    final_action = result.get(
        "final_action"
    )

    check(
        "Final action generated",
        final_action is not None,
    )

    check(
        "Final action is a string",
        isinstance(
            final_action,
            str,
        ),
    )


# ============================================================
# 10. AGENT TRACE
# ============================================================

def test_agent_trace():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    trace = result.get(
        "agent_trace",
        [],
    )

    check(
        "Agent trace generated",
        isinstance(trace, list),
    )

    required_steps = [
        "CUSTOMER_CONTEXT",
        "BUYER_AGENT",
        "PRODUCT_RETRIEVER",
        "OPPORTUNITY_ENGINE",
        "MERCHANT_DECISION_ENGINE",
        "NEGOTIATION_AGENT",
        "FINAL_DECISION",
    ]

    for step in required_steps:

        check(
            f"Trace contains {step}",
            step in trace,
        )


# ============================================================
# 11. HIGH DISCOUNT REQUEST
# ============================================================

def test_high_discount_request():

    agent = create_agent()

    result = process(
        agent,
        "Give me 50% discount and I'll buy immediately.",
    )

    intent = result.get(
        "customer_intent",
        {},
    )

    policy = result.get(
        "policy"
    )

    final_action = result.get(
        "final_action"
    )

    check(
        "High discount request processed",
        isinstance(result, dict),
    )

    check(
        "High discount detected",
        intent.get("discount_requested")
        is True,
    )

    check(
        "Maximum requested discount extracted",
        intent.get("max_discount_requested")
        == 50,
        expected=50,
        actual=intent.get(
            "max_discount_requested"
        ),
    )

    check(
        "Final action still generated",
        isinstance(
            final_action,
            str,
        ),
    )

    if policy:

        approved = policy.get(
            "approved_discount",
            0,
        )

        check(
            "Approved discount does not exceed request",
            approved <= 50,
        )


# ============================================================
# 12. PAYMENT SAFETY
# ============================================================

def test_payment_safety():

    agent = create_agent()

    result = process(
        agent,
        "I want a product under ₹2000.",
    )

    payment = result.get(
        "payment"
    )

    order = result.get(
        "order"
    )

    check(
        "Payment not executed during integration test",
        payment is None,
    )

    check(
        "Order not created during integration test",
        order is None,
    )


# ============================================================
# 13. EMPTY MESSAGE
# ============================================================

def test_empty_message():

    agent = create_agent()

    raised = False

    try:

        agent.process(
            message="",
            customer_id=CUSTOMER_ID,
            execute_payment=False,
        )

    except ValueError:

        raised = True

    check(
        "Empty customer message rejected",
        raised is True,
    )


# ============================================================
# 14. UNKNOWN CUSTOMER
# ============================================================

def test_unknown_customer():

    agent = create_agent()

    unknown_customer_id = 999999999

    print("\n" + "=" * 80)
    print("UNKNOWN CUSTOMER DEBUG")
    print("=" * 80)

    try:
        result = agent.process(
            message="I want a product under ₹2000.",
            customer_id=999999999,
            execute_payment=False,
        )

        print("[DEBUG] Pipeline completed successfully")
        print("[DEBUG] Result type:", type(result).__name__)
        print("[DEBUG] Result:", result)

        assert result is not None

        print("[PASS] Unknown customer does not crash pipeline")

    except Exception as exc:
        print("[FAIL] Unknown customer does not crash pipeline")
        print()
        print("EXCEPTION TYPE:")
        print(type(exc).__name__)
        print()
        print("EXCEPTION:")
        print(exc)
        print()

        import traceback
        traceback.print_exc()


# ============================================================
# 15. NO PAYMENT EXECUTION FLAG
# ============================================================

def test_payment_flag_disabled():

    agent = create_agent()

    result = agent.process(
        message="I like this product but can you give me 10% off?",
        customer_id=CUSTOMER_ID,
        payment_method="UPI",
        execute_payment=False,
        simulate_failure=False,
    )

    check(
        "Payment execution disabled",
        result.get("payment") is None,
    )

    check(
        "Order creation disabled without payment",
        result.get("order") is None,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global passed, failed

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 05 — CUSTOMER-AWARE COMMERCE AGENT TEST SUITE")
    print("=" * 80)

    print()
    print(
        "Payment execution: DISABLED"
    )

    print(
        f"Customer ID: {CUSTOMER_ID}"
    )

    # --------------------------------------------------------
    # BASIC PIPELINE
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("CUSTOMER-AWARE PIPELINE TESTS")
    print("-" * 80)

    test_basic_request()
    test_customer_context()
    test_buyer_agent()
    test_product_retrieval()
    test_opportunity_engine()

    # --------------------------------------------------------
    # COMMERCE DECISION
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("COMMERCE DECISION TESTS")
    print("-" * 80)

    test_merchant_decision()
    test_negotiation()
    test_policy()
    test_final_decision()

    # --------------------------------------------------------
    # EXPLAINABILITY / TRACE
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("TRACE / SAFETY TESTS")
    print("-" * 80)

    test_agent_trace()
    test_high_discount_request()
    test_payment_safety()

    # --------------------------------------------------------
    # EDGE CASES
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("EDGE CASE TESTS")
    print("-" * 80)

    test_empty_message()
    test_unknown_customer()
    test_payment_flag_disabled()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total = passed + failed

    print()
    print("=" * 80)
    print("PHASE 05 COMMERCE AGENT TEST SUMMARY")
    print("=" * 80)

    print(f"Total tests : {total}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")

    print()

    if failed == 0:

        print("=" * 80)
        print("ALL PHASE 05 COMMERCE AGENT TESTS PASSED")
        print("=" * 80)

        return 0

    else:

        print("=" * 80)
        print("PHASE 05 COMMERCE AGENT TESTS FAILED")
        print("=" * 80)

        return 1


if __name__ == "__main__":
    sys.exit(main())
