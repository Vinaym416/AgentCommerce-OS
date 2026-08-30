
"""
AGENTCOMMERCE OS
PHASE 08 — POLICY ENGINE TEST SUITE

Tests the deterministic merchant policy engine.

This test suite verifies:

    1. Discount policy
    2. Discount capping
    3. Purchase-intent requirement
    4. Negotiation limits
    5. Negotiation order threshold
    6. Order approval rules
    7. Agent permissions

Important:
    These tests do NOT use an LLM.

    The Policy Engine is the deterministic authority.
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
# POLICY ENGINE
# ============================================================

from script.policy.policy_engine import PolicyEngine


# ============================================================
# TEST HELPERS
# ============================================================

PASSED = 0
FAILED = 0


def test(name, condition, details=""):
    """
    Simple test runner.
    """

    global PASSED
    global FAILED

    if condition:

        print(f"[PASS] {name}")
        PASSED += 1

    else:

        print(f"[FAIL] {name}")

        if details:
            print(f"       {details}")

        FAILED += 1


def expect_equal(
    name,
    actual,
    expected,
):
    test(
        name,
        actual == expected,
        f"Expected: {expected} | Actual: {actual}",
    )


# ============================================================
# INITIALIZE ENGINE
# ============================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 08 — POLICY ENGINE TEST SUITE")
    print("=" * 80)

    engine = PolicyEngine()

    print()
    print("Policy Engine initialized.")
    print()


    # ========================================================
    # 1. DISCOUNT WITHIN POLICY
    # ========================================================

    result = engine.evaluate_discount(
        product_price=2799,
        requested_discount_percent=5,
        purchase_opportunity_score=0.80,
    )

    expect_equal(
        "Discount within policy is allowed",
        result["allowed"],
        True,
    )

    expect_equal(
        "5% discount is approved",
        result["approved_discount_percent"],
        5,
    )


    # ========================================================
    # 2. DISCOUNT LIMIT
    # ========================================================

    result = engine.evaluate_discount(
        product_price=2799,
        requested_discount_percent=20,
        purchase_opportunity_score=0.80,
    )

    expect_equal(
        "Excessive discount is capped",
        result["approved_discount_percent"],
        10,
    )

    expect_equal(
        "Capped discount is allowed",
        result["allowed"],
        True,
    )

    expect_equal(
        "Final price after 10% cap",
        result["final_price"],
        2519.10,
    )


    # ========================================================
    # 3. LOW PURCHASE INTENT
    # ========================================================

    result = engine.evaluate_discount(
        product_price=2799,
        requested_discount_percent=5,
        purchase_opportunity_score=0.40,
    )

    expect_equal(
        "Low purchase intent blocks discount",
        result["allowed"],
        False,
    )

    expect_equal(
        "Low purchase intent reason",
        result["reason"],
        "insufficient_purchase_intent",
    )


    # ========================================================
    # 4. NEGOTIATION ALLOWED
    # ========================================================

    result = engine.evaluate_negotiation(
        order_value=1500,
        requested_discount_percent=5,
        negotiation_round=1,
    )

    expect_equal(
        "Valid negotiation is allowed",
        result["allowed"],
        True,
    )

    expect_equal(
        "Valid negotiation reason",
        result["reason"],
        "negotiation_allowed",
    )


    # ========================================================
    # 5. NEGOTIATION ORDER VALUE
    # ========================================================

    result = engine.evaluate_negotiation(
        order_value=100,
        requested_discount_percent=5,
        negotiation_round=1,
    )

    expect_equal(
        "Low-value order cannot negotiate",
        result["allowed"],
        False,
    )

    expect_equal(
        "Low-value negotiation reason",
        result["reason"],
        "order_value_below_negotiation_threshold",
    )


    # ========================================================
    # 6. NEGOTIATION ROUND LIMIT
    # ========================================================

    result = engine.evaluate_negotiation(
        order_value=1500,
        requested_discount_percent=5,
        negotiation_round=2,
    )

    expect_equal(
        "Maximum negotiation rounds enforced",
        result["allowed"],
        False,
    )

    expect_equal(
        "Negotiation limit reason",
        result["reason"],
        "maximum_negotiation_rounds_reached",
    )


    # ========================================================
    # 7. NEGOTIATION DISCOUNT LIMIT
    # ========================================================

    result = engine.evaluate_negotiation(
        order_value=1500,
        requested_discount_percent=15,
        negotiation_round=1,
    )

    expect_equal(
        "Negotiation cannot exceed discount policy",
        result["allowed"],
        False,
    )

    expect_equal(
        "Negotiation discount-limit reason",
        result["reason"],
        "requested_discount_exceeds_discount_policy",
    )


    # ========================================================
    # 8. ORDER AUTO APPROVAL
    # ========================================================

    result = engine.evaluate_order_approval(
        order_value=1500,
    )

    expect_equal(
        "Eligible order gets approval decision",
        result["status"],
        "AUTO_APPROVED",
    )

    expect_equal(
        "Auto approval reason",
        result["reason"],
        "below_auto_approval_threshold",
    )


    # ========================================================
    # 9. ORDER HUMAN APPROVAL
    # ========================================================

    # Determine a value above the configured
    # human-approval threshold.

    approval_policy = engine.policy[
        "approval_policy"
    ]

    human_threshold = approval_policy[
        "require_approval_above"
    ]

    result = engine.evaluate_order_approval(
        order_value=human_threshold,
    )

    expect_equal(
        "High-value order requires human approval",
        result["status"],
        "HUMAN_APPROVAL_REQUIRED",
    )

    expect_equal(
        "Human approval reason",
        result["reason"],
        "order_exceeds_approval_threshold",
    )


    # ========================================================
    # 10. STANDARD APPROVAL
    # ========================================================

    auto_threshold = approval_policy[
        "auto_approve_below"
    ]

    standard_value = (
        auto_threshold
        + (
            human_threshold
            - auto_threshold
        ) / 2
    )

    result = engine.evaluate_order_approval(
        order_value=standard_value,
    )

    expect_equal(
        "Intermediate order uses standard approval",
        result["status"],
        "STANDARD_APPROVAL",
    )

    expect_equal(
        "Standard approval reason",
        result["reason"],
        "order_within_standard_threshold",
    )


    # ========================================================
    # 11. PAYMENT ORDER PERMISSION
    # ========================================================

    can_create_payment_order = (
        engine.can_agent_execute(
            "can_create_payment_order"
        )
    )

    expect_equal(
        "Agent can create payment order",
        can_create_payment_order,
        True,
    )


    # ========================================================
    # 12. PAYMENT EXECUTION PERMISSION
    # ========================================================

    can_execute_payment = (
        engine.can_agent_execute(
            "can_execute_payment"
        )
    )

    expect_equal(
        "Agent cannot directly execute payment",
        can_execute_payment,
        False,
    )


    # ========================================================
    # 13. UNKNOWN PERMISSION
    # ========================================================

    unknown_permission = (
        engine.can_agent_execute(
            "some_unknown_financial_permission"
        )
    )

    expect_equal(
        "Unknown permission is denied",
        unknown_permission,
        False,
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    total = PASSED + FAILED

    print()
    print("=" * 80)
    print("POLICY ENGINE TEST SUMMARY")
    print("=" * 80)

    print(f"Total tests : {total}")
    print(f"Passed      : {PASSED}")
    print(f"Failed      : {FAILED}")

    print()

    if FAILED == 0:

        print("=" * 80)
        print("ALL POLICY ENGINE TESTS PASSED")
        print("=" * 80)

        return 0

    else:

        print("=" * 80)
        print("POLICY ENGINE TESTS FAILED")
        print("=" * 80)

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(main())

