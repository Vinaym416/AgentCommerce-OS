"""
AGENTCOMMERCE OS
SESSION + CUSTOMER + PRODUCT OPPORTUNITY ENGINE
"""

from typing import Optional


class OpportunityEngine:

    def calculate(
        self,
        *,
        intent,
        product,
        customer: Optional[dict] = None
    ):

        product_score = float(
            getattr(product, "product_score", 0.5)
            if not isinstance(product, dict)
            else product.get("popularity_score", product.get("product_score", 0.5))
        )

        if customer:
            customer_affinity = float(customer.get("affinity_score", customer.get("customer_affinity_score", 0.5)))
            discount_dependence = float(customer.get("discount_dependence", customer.get("discount_dependence_score", 0.5)))
            buying_confidence = float(customer.get("customer_buying_confidence", 0.5))
        else:
            customer_affinity = 0.5
            discount_dependence = 0.5
            buying_confidence = 0.5

        urgency_map = {
            "low": 0.25,
            "medium": 0.55,
            "normal": 0.55,
            "high": 0.9,
        }
        urgency_score = urgency_map.get(getattr(intent, "urgency", None) or (intent.get("urgency") if isinstance(intent, dict) else "medium"), 0.55)

        intent_name = getattr(intent, "intent", None) or (intent.get("intent") if isinstance(intent, dict) else "PRODUCT_SEARCH")
        purchase_intent_score = 1.0 if str(intent_name).lower() in {"purchase", "product_search", "accept"} else 0.5

        price_sensitivity = 1.0 - min(1.0, max(0.0, discount_dependence))

        purchase_score = (
            0.30 * product_score
            + 0.25 * buying_confidence
            + 0.20 * customer_affinity
            + 0.15 * urgency_score
            + 0.10 * purchase_intent_score
        )
        purchase_score = max(0.0, min(1.0, purchase_score))

        discount_score = (
            0.55 * discount_dependence
            + 0.25 * (1.0 - purchase_score)
            + 0.20 * (1.0 if getattr(intent, "discount_requested", False) or (isinstance(intent, dict) and intent.get("discount_requested")) else 0.0)
        )
        discount_score = max(0.0, min(1.0, discount_score))

        churn_risk = max(0.0, min(1.0, 1.0 - purchase_score + (0.3 * price_sensitivity)))

        if customer_affinity >= 0.75 and discount_dependence >= 0.65:
            reasoning = "High affinity customer with strong discount sensitivity."
        elif customer_affinity >= 0.7:
            reasoning = "High affinity customer, likely to convert without heavy discounting."
        elif discount_dependence >= 0.6:
            reasoning = "Price-sensitive customer; discount may be needed to close the deal."
        else:
            reasoning = "Balanced customer profile; purchase intent is moderate and discount impact is limited."

        return {
            "purchase_opportunity_score": round(purchase_score, 4),
            "discount_opportunity_score": round(discount_score, 4),
            "churn_risk": round(churn_risk, 4),
            "reasoning": reasoning,
        }


if __name__ == "__main__":

    print(
        "OpportunityEngine loaded successfully."
    )