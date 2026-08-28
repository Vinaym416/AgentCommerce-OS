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

        # --------------------------------------------------
        # PRODUCT SIGNAL
        # --------------------------------------------------

        product_score = float(
            product.product_score
        )

        # --------------------------------------------------
        # CUSTOMER SIGNAL
        # --------------------------------------------------

        if customer:

            customer_confidence = float(
                customer[
                    "customer_buying_confidence"
                ]
            )

            discount_dependence = float(
                customer[
                    "discount_dependence_score"
                ]
            )

            customer_affinity = float(
                customer[
                    "customer_affinity_score"
                ]
            )

        else:

            # Anonymous user fallback
            customer_confidence = 0.50
            discount_dependence = 0.25
            customer_affinity = 0.50

        # --------------------------------------------------
        # INTENT SIGNAL
        # --------------------------------------------------

        urgency_score = {
            "low": 0.25,
            "normal": 0.50,
            "high": 0.90
        }.get(
            intent.urgency,
            0.50
        )

        explicit_purchase_score = (
            1.0
            if intent.intent == "purchase"
            else 0.50
        )

        # --------------------------------------------------
        # PURCHASE OPPORTUNITY
        # --------------------------------------------------

        purchase_score = (
            0.25 * product_score
            +
            0.25 * customer_confidence
            +
            0.20 * customer_affinity
            +
            0.15 * urgency_score
            +
            0.15 * explicit_purchase_score
        )

        purchase_score = max(
            0.0,
            min(
                1.0,
                purchase_score
            )
        )

        # --------------------------------------------------
        # DISCOUNT OPPORTUNITY
        # --------------------------------------------------

        explicit_discount = (
            1.0
            if intent.discount_requested
            else 0.0
        )

        discount_score = (
            0.45 * discount_dependence
            +
            0.30 * explicit_discount
            +
            0.25 * (
                1.0
                - purchase_score
            )
        )

        discount_score = max(
            0.0,
            min(
                1.0,
                discount_score
            )
        )

        return {
            "purchase_opportunity_score": round(
                purchase_score,
                4
            ),

            "discount_opportunity_score": round(
                discount_score,
                4
            )
        }


if __name__ == "__main__":

    print(
        "OpportunityEngine loaded successfully."
    )