import json
from pathlib import Path

import pandas as pd
from script.agents.schemas import MerchantDecision


BASE_DIR = Path(__file__).resolve().parents[2]

BASELINE_PATH = (
    BASE_DIR
    / "data"
    / "intelligence"
    / "baseline_decisions.csv"
)

POLICY_PATH = (
    BASE_DIR
    / "data"
    / "policies"
    / "merchant_policy.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "data"
    / "policies"
    / "merchant_decisions.csv"
)


def load_policy():

    with open(
        POLICY_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def decide_action(row, policy):

    purchase_score = float(
        row["purchase_opportunity_score"]
    )

    discount_score = float(
        row["discount_opportunity_score"]
    )

    merchant_score = float(
        row["merchant_growth_score"]
    )

    product_price = float(
        row.get("unit_price", 0)
    )

    max_discount = policy[
        "discount_policy"
    ]["max_discount_percent"]

    minimum_order_value = policy[
        "negotiation_policy"
    ]["minimum_order_value"]

    max_rounds = policy[
        "negotiation_policy"
    ]["max_rounds"]

    auto_approve_below = policy[
        "approval_policy"
    ]["auto_approve_below"]

    require_approval_above = policy[
        "approval_policy"
    ]["require_approval_above"]

    reasons = []

    # ==================================================
    # 1. LOW INTENT
    # ==================================================

    if purchase_score < 0.40:

        return {
            "merchant_action": "NO_ACTION",
            "approved_discount_percent": 0,
            "negotiation_allowed": False,
            "approval_status": "NOT_REQUIRED",
            "decision_reasons": [
                "low_purchase_intent"
            ]
        }

    # ==================================================
    # 2. HIGH PURCHASE INTENT
    # ==================================================

    if purchase_score >= 0.75:

        reasons.append(
            "high_purchase_intent"
        )

        # Strong intent means don't unnecessarily
        # sacrifice merchant margin.

        if discount_score < 0.40:

            reasons.append(
                "low_discount_need"
            )

            return {
                "merchant_action": "NO_DISCOUNT",
                "approved_discount_percent": 0,
                "negotiation_allowed": False,
                "approval_status": (
                    "AUTO_APPROVED"
                    if product_price < auto_approve_below
                    else "STANDARD_APPROVAL"
                ),
                "decision_reasons": reasons
            }

    # ==================================================
    # 3. LIMITED OFFER
    # ==================================================

    if (
        purchase_score >= 0.40
        and discount_score >= 0.40
        and discount_score < 0.65
    ):

        reasons.append(
            "moderate_discount_opportunity"
        )

        approved_discount = min(
            10,
            max_discount
        )

        return {
            "merchant_action": "LIMITED_OFFER",
            "approved_discount_percent": approved_discount,
            "negotiation_allowed": False,
            "approval_status": (
                "AUTO_APPROVED"
                if product_price < auto_approve_below
                else "STANDARD_APPROVAL"
            ),
            "decision_reasons": reasons
        }

    # ==================================================
    # 4. NEGOTIATION
    # ==================================================

    if (
        purchase_score >= 0.60
        and discount_score >= 0.65
        and product_price >= minimum_order_value
    ):

        reasons.append(
            "high_discount_opportunity"
        )

        reasons.append(
            "negotiation_threshold_reached"
        )

        return {
            "merchant_action": "NEGOTIATE",
            "approved_discount_percent": max_discount,
            "negotiation_allowed": True,
            "max_negotiation_rounds": max_rounds,
            "approval_status": (
                "HUMAN_APPROVAL_REQUIRED"
                if product_price >= require_approval_above
                else "STANDARD_APPROVAL"
            ),
            "decision_reasons": reasons
        }

    # ==================================================
    # 5. DEFAULT
    # ==================================================

    return {
        "merchant_action": "CONTINUE_ENGAGEMENT",
        "approved_discount_percent": 0,
        "negotiation_allowed": False,
        "approval_status": "NOT_REQUIRED",
        "decision_reasons": [
            "continue_customer_engagement"
        ]
    }


class MerchantDecisionEngine:
    def __init__(self, policy_path=POLICY_PATH):
        self.policy = load_policy()

    def decide(
        self,
        product_id,
        purchase_opportunity_score,
        discount_opportunity_score,
        product_price=0,
    ) -> MerchantDecision:
        row = {
            "product_id": product_id,
            "purchase_opportunity_score": purchase_opportunity_score,
            "discount_opportunity_score": discount_opportunity_score,
            "merchant_growth_score": 0,
            "unit_price": product_price,
        }

        decision = decide_action(row, self.policy)

        return MerchantDecision(
            merchant_action=decision["merchant_action"],
            approved_discount_percent=decision[
                "approved_discount_percent"
            ],
            negotiation_allowed=decision["negotiation_allowed"],
            approval_status=decision["approval_status"],
            reason=", ".join(decision.get("decision_reasons", [])),
        )


def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS - MERCHANT DECISION ENGINE")
    print("=" * 80)

    df = pd.read_csv(
        BASELINE_PATH
    )

    policy = load_policy()

    print()
    print(f"Loaded sessions : {len(df):,}")
    print(
        f"Maximum discount: "
        f"{policy['discount_policy']['max_discount_percent']}%"
    )

    decisions = []

    for _, row in df.iterrows():

        decision = decide_action(
            row,
            policy
        )

        decisions.append(decision)

    decision_df = pd.DataFrame(
        decisions
    )

    result = pd.concat(
        [
            df.reset_index(drop=True),
            decision_df
        ],
        axis=1
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print()
    print("=" * 80)
    print("MERCHANT DECISION DISTRIBUTION")
    print("=" * 80)

    print(
        result[
            "merchant_action"
        ].value_counts()
    )

    print()
    print("=" * 80)
    print("APPROVAL DISTRIBUTION")
    print("=" * 80)

    print(
        result[
            "approval_status"
        ].value_counts()
    )

    print()
    print("=" * 80)
    print("DISCOUNT DISTRIBUTION")
    print("=" * 80)

    print(
        result[
            "approved_discount_percent"
        ].value_counts()
        .sort_index()
    )

    print()
    print("Top decisions:")

    columns = [
        "session_id",
        "customer_id",
        "product_id",
        "purchase_opportunity_score",
        "discount_opportunity_score",
        "merchant_action",
        "approved_discount_percent",
        "negotiation_allowed",
        "approval_status"
    ]

    print(
        result[columns]
        .head(15)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print(OUTPUT_PATH)

    print()
    print("PHASE 02 STEP 02 COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()