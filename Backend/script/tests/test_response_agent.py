"""
AGENTCOMMERCE OS
PHASE 09 — RESPONSE / EXPLAINABILITY AGENT TEST SUITE

Tests:
1. Normal recommendation explanation
2. NO_ACTION explanation
3. NO_DISCOUNT explanation
4. LIMITED_OFFER explanation
5. NEGOTIATE explanation
6. Policy DENY explanation
7. Policy MODIFY explanation
8. Policy ESCALATE explanation
9. Missing product handling
10. Missing merchant/policy decision handling
11. Trace generation
12. Metadata generation
"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.agents.schemas import (
    BuyerIntent,
    ProductCandidate,
    MerchantDecision,
    PolicyResult,
)

from script.agents.response_agent import ResponseAgent


# ============================================================
# TEST HELPERS
# ============================================================

passed = 0
failed = 0


def check(test_name, condition, expected=None, actual=None):

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
            print(f"       Actual: {actual}")


# ============================================================
# FIXTURES
# ============================================================

def create_intent():

    return BuyerIntent(
        intent="product_search",
        budget=3000,
        urgency="normal",
        discount_requested=False,
        product_preferences=["smartphone"],
        constraints=[],
        confidence=0.92,
    )


def create_product():

    return ProductCandidate(
        product_id=453,
        category_name="Electronics",
        current_price=2499.0,
        conversion_rate=0.18,
        demand_score=0.82,
        quality_score=0.91,
        product_score=0.88,
        rating=4.5,
    )


def create_merchant_decision(
    action="LIMITED_OFFER",
    discount=10.0,
    negotiation=False,
    approval="STANDARD_APPROVAL",
    reason="moderate_discount_opportunity",
):

    return MerchantDecision(
        merchant_action=action,
        approved_discount_percent=discount,
        negotiation_allowed=negotiation,
        approval_status=approval,
        reason=reason,
    )


def create_policy_result(
    allowed=True,
    discount=10.0,
    discount_amount=249.9,
    final_price=2249.1,
    reasons=None,
):

    if reasons is None:
        reasons = [
            "discount_within_merchant_policy"
        ]

    return PolicyResult(
        allowed=allowed,
        approved_discount_percent=discount,
        discount_amount=discount_amount,
        final_price=final_price,
        reasons=reasons,
    )


# ============================================================
# RESPONSE AGENT FACTORY
# ============================================================

def create_agent():

    return ResponseAgent()


# ============================================================
# 1. NORMAL RECOMMENDATION
# ============================================================

def test_normal_recommendation():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="LIMITED_OFFER",
        discount=10,
        negotiation=False,
        approval="STANDARD_APPROVAL",
        reason="moderate_discount_opportunity",
    )

    policy_result = create_policy_result()

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Normal recommendation returns response",
        response is not None,
    )

    check(
        "Normal recommendation contains message",
        bool(response.message),
    )

    check(
        "Normal recommendation contains product",
        len(response.products) == 1,
    )


# ============================================================
# 2. NO ACTION
# ============================================================

def test_no_action():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="NO_ACTION",
        discount=0,
        negotiation=False,
        approval="NOT_REQUIRED",
        reason="low_purchase_intent",
    )

    policy_result = create_policy_result(
        allowed=False,
        discount=0,
        discount_amount=0,
        final_price=2499,
        reasons=[
            "insufficient_purchase_intent"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "NO_ACTION response generated",
        response is not None,
    )

    check(
        "NO_ACTION message generated",
        bool(response.message),
    )

    check(
        "NO_ACTION merchant decision preserved",
        response.merchant_decision.merchant_action
        == "NO_ACTION",
    )


# ============================================================
# 3. NO DISCOUNT
# ============================================================

def test_no_discount():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="NO_DISCOUNT",
        discount=0,
        negotiation=False,
        approval="AUTO_APPROVED",
        reason="low_discount_need",
    )

    policy_result = create_policy_result(
        allowed=True,
        discount=0,
        discount_amount=0,
        final_price=2499,
        reasons=[
            "discount_within_merchant_policy"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "NO_DISCOUNT response generated",
        response is not None,
    )

    check(
        "NO_DISCOUNT message generated",
        bool(response.message),
    )

    check(
        "NO_DISCOUNT decision preserved",
        response.merchant_decision.merchant_action
        == "NO_DISCOUNT",
    )


# ============================================================
# 4. LIMITED OFFER
# ============================================================

def test_limited_offer():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="LIMITED_OFFER",
        discount=10,
        negotiation=False,
        approval="STANDARD_APPROVAL",
        reason="moderate_discount_opportunity",
    )

    policy_result = create_policy_result(
        allowed=True,
        discount=10,
        discount_amount=249.9,
        final_price=2249.1,
        reasons=[
            "discount_within_merchant_policy"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "LIMITED_OFFER response generated",
        response is not None,
    )

    check(
        "LIMITED_OFFER contains discount",
        response.policy_result.approved_discount_percent
        == 10,
    )


# ============================================================
# 5. NEGOTIATION
# ============================================================

def test_negotiation():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="NEGOTIATE",
        discount=10,
        negotiation=True,
        approval="STANDARD_APPROVAL",
        reason="high_discount_opportunity",
    )

    policy_result = create_policy_result(
        allowed=True,
        discount=10,
        discount_amount=249.9,
        final_price=2249.1,
        reasons=[
            "discount_within_merchant_policy"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "NEGOTIATE response generated",
        response is not None,
    )

    check(
        "Negotiation permission preserved",
        response.merchant_decision.negotiation_allowed
        is True,
    )


# ============================================================
# 6. POLICY DENY
# ============================================================

def test_policy_deny():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="LIMITED_OFFER",
        discount=0,
        negotiation=False,
        approval="NOT_REQUIRED",
        reason="policy_rejected",
    )

    policy_result = create_policy_result(
        allowed=False,
        discount=0,
        discount_amount=0,
        final_price=0,
        reasons=[
            "minimum_margin_violated"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Policy DENY response generated",
        response is not None,
    )

    check(
        "Policy DENY contains policy result",
        response.policy_result.allowed is False,
    )


# ============================================================
# 7. POLICY MODIFY
# ============================================================

def test_policy_modify():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="LIMITED_OFFER",
        discount=10,
        negotiation=False,
        approval="STANDARD_APPROVAL",
        reason="discount_capped_by_policy",
    )

    policy_result = create_policy_result(
        allowed=True,
        discount=8,
        discount_amount=199.92,
        final_price=2299.08,
        reasons=[
            "discount_capped_by_policy"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Policy MODIFY response generated",
        response is not None,
    )

    check(
        "Modified discount preserved",
        response.policy_result.approved_discount_percent
        == 8,
    )


# ============================================================
# 8. POLICY ESCALATE / HUMAN APPROVAL
# ============================================================

def test_policy_escalation():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision(
        action="NEGOTIATE",
        discount=10,
        negotiation=True,
        approval="HUMAN_APPROVAL_REQUIRED",
        reason="order_exceeds_approval_threshold",
    )

    policy_result = create_policy_result(
        allowed=False,
        discount=10,
        discount_amount=249.9,
        final_price=2249.1,
        reasons=[
            "merchant_approval_required"
        ],
    )

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Escalation response generated",
        response is not None,
    )

    check(
        "Human approval status preserved",
        response.merchant_decision.approval_status
        == "HUMAN_APPROVAL_REQUIRED",
    )


# ============================================================
# 9. MISSING PRODUCT
# ============================================================

def test_missing_product():

    agent = create_agent()

    intent = create_intent()

    merchant_decision = create_merchant_decision(
        action="NO_ACTION",
        discount=0,
        negotiation=False,
        approval="NOT_REQUIRED",
        reason="product_not_found",
    )

    policy_result = None

    response = agent.generate_response(
        intent=intent,
        products=[],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Missing product handled safely",
        response is not None,
    )

    check(
        "Missing product still returns message",
        bool(response.message),
    )

    check(
        "Missing product returns empty product list",
        len(response.products) == 0,
    )


# ============================================================
# 10. MISSING DECISIONS
# ============================================================

def test_missing_decisions():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=None,
        policy_result=None,
    )

    check(
        "Missing decisions handled safely",
        response is not None,
    )

    check(
        "Missing decisions still return message",
        bool(response.message),
    )


# ============================================================
# 11. TRACE
# ============================================================

def test_trace():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision()

    policy_result = create_policy_result()

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Trace is generated",
        isinstance(response.trace, list),
    )

    check(
        "Trace contains intent_parsed",
        "intent_parsed" in response.trace,
    )

    check(
        "Trace contains catalog_searched",
        "catalog_searched" in response.trace,
    )

    check(
        "Trace contains product_selected",
        "product_selected" in response.trace,
    )

    check(
        "Trace contains merchant_decision_generated",
        "merchant_decision_generated" in response.trace,
    )

    check(
        "Trace contains policy_checked",
        "policy_checked" in response.trace,
    )


# ============================================================
# 12. METADATA
# ============================================================

def test_metadata():

    agent = create_agent()

    intent = create_intent()
    product = create_product()

    merchant_decision = create_merchant_decision()

    policy_result = create_policy_result()

    response = agent.generate_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
    )

    check(
        "Metadata is generated",
        isinstance(response.metadata, dict),
    )

    check(
        "Phase metadata exists",
        response.metadata.get("phase") == 9,
    )

    check(
        "Explainability metadata enabled",
        response.metadata.get("explainability") is True,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global passed, failed

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 09 — RESPONSE / EXPLAINABILITY AGENT TEST SUITE")
    print("=" * 80)

    print()
    print("Response Agent initialized.")

    print()
    print("-" * 80)
    print("BASIC RESPONSE TESTS")
    print("-" * 80)

    test_normal_recommendation()
    test_no_action()
    test_no_discount()
    test_limited_offer()
    test_negotiation()

    print()
    print("-" * 80)
    print("POLICY RESPONSE TESTS")
    print("-" * 80)

    test_policy_deny()
    test_policy_modify()
    test_policy_escalation()

    print()
    print("-" * 80)
    print("EDGE CASE TESTS")
    print("-" * 80)

    test_missing_product()
    test_missing_decisions()

    print()
    print("-" * 80)
    print("EXPLAINABILITY TESTS")
    print("-" * 80)

    test_trace()
    test_metadata()

    total = passed + failed

    print()
    print("=" * 80)
    print("PHASE 09 RESPONSE AGENT TEST SUMMARY")
    print("=" * 80)

    print(f"Total tests : {total}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")

    print()

    if failed == 0:

        print("=" * 80)
        print("ALL PHASE 09 RESPONSE AGENT TESTS PASSED")
        print("=" * 80)

    else:

        print("=" * 80)
        print("PHASE 09 RESPONSE AGENT TESTS FAILED")
        print("=" * 80)


if __name__ == "__main__":
    main()