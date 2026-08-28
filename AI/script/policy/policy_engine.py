import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

POLICY_PATH = (
    BASE_DIR
    / "data"
    / "policies"
    / "merchant_policy.json"
)


class PolicyEngine:

    def __init__(self, policy_path=POLICY_PATH):

        self.policy_path = Path(policy_path)

        with open(
            self.policy_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.policy = json.load(f)

    # ==================================================
    # DISCOUNT
    # ==================================================

    def evaluate_discount(
        self,
        product_price,
        requested_discount_percent,
        purchase_opportunity_score
    ):

        discount_policy = self.policy[
            "discount_policy"
        ]

        reasons = []

        # ------------------------------------------------
        # Discount globally disabled
        # ------------------------------------------------

        if not discount_policy["enabled"]:

            return {
                "allowed": False,
                "approved_discount_percent": 0,
                "reason": "discount_disabled"
            }

        # ------------------------------------------------
        # Check maximum discount
        # ------------------------------------------------

        max_discount = discount_policy[
            "max_discount_percent"
        ]

        if requested_discount_percent > max_discount:

            reasons.append(
                "requested_discount_exceeds_policy_limit"
            )

            requested_discount_percent = max_discount

        # ------------------------------------------------
        # Check purchase intent
        # ------------------------------------------------

        if (
            discount_policy[
                "discount_requires_high_intent"
            ]
            and purchase_opportunity_score < 0.60
        ):

            return {
                "allowed": False,
                "approved_discount_percent": 0,
                "reason": "insufficient_purchase_intent"
            }

        # ------------------------------------------------
        # Calculate final price
        # ------------------------------------------------

        discount_amount = (
            product_price
            * requested_discount_percent
            / 100
        )

        final_price = (
            product_price
            - discount_amount
        )

        if requested_discount_percent == max_discount:

            reasons.append(
                "discount_capped_by_merchant_policy"
            )

        else:

            reasons.append(
                "discount_within_merchant_policy"
            )

        return {
            "allowed": True,
            "approved_discount_percent": round(
                requested_discount_percent,
                2
            ),
            "discount_amount": round(
                discount_amount,
                2
            ),
            "final_price": round(
                final_price,
                2
            ),
            "reasons": reasons
        }

    # ==================================================
    # NEGOTIATION
    # ==================================================

    def evaluate_negotiation(
        self,
        order_value,
        requested_discount_percent,
        negotiation_round
    ):

        policy = self.policy[
            "negotiation_policy"
        ]

        if not policy["enabled"]:

            return {
                "allowed": False,
                "reason": "negotiation_disabled"
            }

        if (
            order_value
            < policy["minimum_order_value"]
        ):

            return {
                "allowed": False,
                "reason": "order_value_below_negotiation_threshold"
            }

        if (
            negotiation_round
            >= policy["max_rounds"]
        ):

            return {
                "allowed": False,
                "reason": "maximum_negotiation_rounds_reached"
            }

        if (
            requested_discount_percent
            > self.policy[
                "discount_policy"
            ]["max_discount_percent"]
        ):

            return {
                "allowed": False,
                "reason": "requested_discount_exceeds_discount_policy"
            }

        return {
            "allowed": True,
            "reason": "negotiation_allowed"
        }

    # ==================================================
    # ORDER APPROVAL
    # ==================================================

    def evaluate_order_approval(
        self,
        order_value
    ):

        policy = self.policy[
            "approval_policy"
        ]

        if (
            order_value
            < policy["auto_approve_below"]
        ):

            return {
                "status": "AUTO_APPROVED",
                "reason": "below_auto_approval_threshold"
            }

        if (
            order_value
            >= policy["require_approval_above"]
        ):

            return {
                "status": "HUMAN_APPROVAL_REQUIRED",
                "reason": "order_exceeds_approval_threshold"
            }

        return {
            "status": "STANDARD_APPROVAL",
            "reason": "order_within_standard_threshold"
        }

    # ==================================================
    # AGENT PERMISSION
    # ==================================================

    def can_agent_execute(
        self,
        permission
    ):

        permissions = self.policy[
            "agent_permissions"
        ]

        return permissions.get(
            permission,
            False
        )


# ======================================================
# DEMO
# ======================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS - POLICY ENGINE")
    print("=" * 80)

    engine = PolicyEngine()

    # --------------------------------------------------
    # Example discount decision
    # --------------------------------------------------

    result = engine.evaluate_discount(
        product_price=1500,
        requested_discount_percent=20,
        purchase_opportunity_score=0.82
    )

    print()
    print("DISCOUNT TEST")
    print("-" * 80)

    print(result)

    # --------------------------------------------------
    # Negotiation test
    # --------------------------------------------------

    result = engine.evaluate_negotiation(
        order_value=1500,
        requested_discount_percent=10,
        negotiation_round=1
    )

    print()
    print("NEGOTIATION TEST")
    print("-" * 80)

    print(result)

    # --------------------------------------------------
    # Approval test
    # --------------------------------------------------

    result = engine.evaluate_order_approval(
        order_value=1500
    )

    print()
    print("ORDER APPROVAL TEST")
    print("-" * 80)

    print(result)

    # --------------------------------------------------
    # Permission test
    # --------------------------------------------------

    print()
    print("AGENT PERMISSIONS")
    print("-" * 80)

    print(
        "Create payment order:",
        engine.can_agent_execute(
            "can_create_payment_order"
        )
    )

    print(
        "Execute payment:",
        engine.can_agent_execute(
            "can_execute_payment"
        )
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()