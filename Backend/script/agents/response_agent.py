"""
AGENTCOMMERCE OS
PHASE 09 — EXPLAINABILITY / RESPONSE AGENT

Converts structured agent, merchant and policy results
into concise, evidence-backed explanations.

IMPORTANT:
- Does NOT expose LLM chain-of-thought.
- Does NOT make financial decisions.
- Does NOT modify policy results.
- Only explains decisions already produced by trusted components.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.agents.schemas import (
    AgentResponse,
    BuyerIntent,
    ProductCandidate,
    MerchantDecision,
    PolicyResult,
)


class ResponseAgent:

    # ============================================================
    # PRODUCT EXPLANATION
    # ============================================================

    def explain_product_selection(
        self,
        intent: BuyerIntent,
        product: ProductCandidate,
    ) -> Dict[str, Any]:

        evidence = []

        # Budget
        if intent.budget is not None:

            if product.current_price <= intent.budget:
                evidence.append(
                    f"Within budget of ₹{intent.budget:.2f}"
                )

            else:
                evidence.append(
                    f"Price ₹{product.current_price:.2f} exceeds "
                    f"budget of ₹{intent.budget:.2f}"
                )

        # Category
        if intent.product_preferences:

            category = product.category_name.lower()

            if any(
                preference.lower() in category
                for preference in intent.product_preferences
            ):
                evidence.append(
                    "Matches requested product preference"
                )

        # Product quality
        if product.quality_score >= 0.70:

            evidence.append(
                "Strong product quality score"
            )

        # Demand / conversion
        if product.conversion_rate >= 0.10:

            evidence.append(
                "Strong historical conversion signal"
            )

        if product.demand_score >= 0.70:

            evidence.append(
                "Strong demand signal"
            )

        # Rating
        if product.rating >= 4.0:

            evidence.append(
                f"Good customer rating ({product.rating:.1f}/5)"
            )

        return {
            "product_id": product.product_id,
            "evidence": evidence,
            "product_score": product.product_score,
        }

    # ============================================================
    # MERCHANT DECISION EXPLANATION
    # ============================================================

    def explain_merchant_decision(
        self,
        decision: MerchantDecision,
    ) -> Dict[str, Any]:

        reasons = []

        if decision.reason:

            reasons = [
                reason.strip()
                for reason in decision.reason.split(",")
                if reason.strip()
            ]

        return {
            "merchant_action": decision.merchant_action,
            "approved_discount_percent": (
                decision.approved_discount_percent
            ),
            "negotiation_allowed": (
                decision.negotiation_allowed
            ),
            "approval_status": (
                decision.approval_status
            ),
            "reasons": reasons,
        }

    # ============================================================
    # POLICY EXPLANATION
    # ============================================================

    def explain_policy_result(
        self,
        result: PolicyResult,
    ) -> Dict[str, Any]:

        reason_codes = [
            str(reason)
            for reason in result.reasons
        ]

        return {
            "decision": (
                result.allowed
            ),
            "approved_discount_percent": (
                result.approved_discount_percent
            ),
            "discount_amount": (
                result.discount_amount
            ),
            "final_price": (
                result.final_price
            ),
            "reason_codes": reason_codes,
        }

    # ============================================================
    # BUILD FINAL RESPONSE
    # ============================================================

    def build_response(
        self,
        intent: BuyerIntent,
        products: List[ProductCandidate],
        merchant_decision: Optional[MerchantDecision] = None,
        policy_result: Optional[PolicyResult] = None,
        final_action: str = "CONTINUE",
        trace: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:

        trace = list(trace) if trace else [
        "intent_parsed",
            "catalog_searched",
         ]

        if products:
            if "product_selected" not in trace:
                trace.append("product_selected")

        if merchant_decision is not None:
            if "merchant_decision_generated" not in trace:
                trace.append("merchant_decision_generated")

        if policy_result is not None:
            if "policy_checked" not in trace:
                trace.append("policy_checked")

        metadata = dict(metadata) if metadata else {}

        metadata.setdefault("phase", 9)
        metadata.setdefault("explainability", True)

        # --------------------------------------------------------
        # Build safe explanation
        # --------------------------------------------------------

        explanation_parts = []

        # Product explanation
        if products:

            selected_product = products[0]

            product_explanation = (
                self.explain_product_selection(
                    intent,
                    selected_product,
                )
            )

            evidence = product_explanation["evidence"]

            if evidence:

                explanation_parts.append(
                    "Product selected because: "
                    + "; ".join(evidence)
                )

        # Merchant explanation
        if merchant_decision:

            merchant_explanation = (
                self.explain_merchant_decision(
                    merchant_decision
                )
            )

            action = merchant_explanation[
                "merchant_action"
            ]

            reasons = merchant_explanation[
                "reasons"
            ]

            explanation_parts.append(
                f"Merchant action: {action}."
            )

            if reasons:

                explanation_parts.append(
                    "Reason: "
                    + "; ".join(reasons)
                    + "."
                )

        # Policy explanation
        if policy_result:

            policy_explanation = (
                self.explain_policy_result(
                    policy_result
                )
            )

            decision = (
                "allowed"
                if policy_explanation["decision"]
                else "denied"
            )

            explanation_parts.append(
                f"Policy decision: {decision}."
            )

            if policy_explanation[
                "reason_codes"
            ]:

                explanation_parts.append(
                    "Policy checks: "
                    + "; ".join(
                        policy_explanation[
                            "reason_codes"
                        ]
                    )
                    + "."
                )

        # --------------------------------------------------------
        # Final user-facing message
        # --------------------------------------------------------

        if explanation_parts:

            message = " ".join(
                explanation_parts
            )

        else:

            message = (
                "The request was processed "
                "using the available commerce signals."
            )

        return AgentResponse(
            intent=intent,
            products=products,
            merchant_decision=merchant_decision,
            policy_result=policy_result,
            final_action=final_action,
            message=message,
            trace=trace,
            metadata=metadata,
        )

    def generate_response(
        self,
        intent: BuyerIntent,
        products: List[ProductCandidate],
        merchant_decision: Optional[MerchantDecision] = None,
        policy_result: Optional[PolicyResult] = None,
        final_action: str = "CONTINUE",
        trace: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        return self.build_response(
            intent=intent,
            products=products,
            merchant_decision=merchant_decision,
            policy_result=policy_result,
            final_action=final_action,
            trace=trace,
            metadata=metadata,
        )


# ==============================================================
# DEMO
# ==============================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print("PHASE 09 — EXPLAINABILITY TEST")
    print("=" * 80)

    agent = ResponseAgent()

    intent = BuyerIntent(
        intent="laptop backpack",
        budget=3000,
        urgency="normal",
        product_preferences=[
            "bags"
        ],
        constraints=[
            "waterproof",
            "16-inch laptop"
        ],
        confidence=0.94,
    )

    product = ProductCandidate(
        product_id=1001,
        category_name="bags",
        current_price=2799,
        conversion_rate=0.14,
        demand_score=0.82,
        quality_score=0.91,
        product_score=0.89,
        rating=4.5,
    )

    merchant_decision = MerchantDecision(
        merchant_action="LIMITED_OFFER",
        approved_discount_percent=10,
        negotiation_allowed=False,
        approval_status="STANDARD_APPROVAL",
        reason=(
            "moderate_discount_opportunity,"
            "discount_capped_by_policy"
        ),
    )

    policy_result = PolicyResult(
        allowed=True,
        approved_discount_percent=10,
        discount_amount=279.90,
        final_price=2519.10,
        reasons=[
            "discount_within_merchant_policy"
        ],
    )

    response = agent.build_response(
        intent=intent,
        products=[product],
        merchant_decision=merchant_decision,
        policy_result=policy_result,
        final_action="OFFER_READY",
        trace=[
            "intent_parsed",
            "catalog_searched",
            "product_selected",
            "merchant_decision_generated",
            "policy_checked",
        ],
        metadata={
            "phase": 9,
            "explainability": True,
        },
    )

    print()
    print("USER-FACING EXPLANATION")
    print("-" * 80)
    print(response.message)

    print()
    print("TRACE")
    print("-" * 80)

    for step in response.trace:
        print(f"→ {step}")

    print()
    print("METADATA")
    print("-" * 80)
    print(response.metadata)

    print()
    print("=" * 80)
    print("PHASE 09 EXPLAINABILITY DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()