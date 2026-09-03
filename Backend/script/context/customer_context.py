"""
AGENTCOMMERCE OS
CUSTOMER CONTEXT ENGINE

Provides deterministic customer/session context to the agent.

The LLM does not invent customer history.

Customer identity comes from the application/session layer.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from script.database.repositories.customer_repository import CustomerRepository


class CustomerContext:

    def __init__(
        self,
        repository=None
    ):
        self.repository = repository or CustomerRepository()

    @staticmethod
    def _anonymous_profile():
        return {
            "customer_id": None,
            "is_known": False,
            "lifetime_value": 0.0,
            "purchase_count": 0,
            "average_discount_taken": 0.0,
            "affinity_score": 0.5,
            "discount_dependence": 0.5,
            "risk_profile": "low",
            "preferred_categories": [],
            "customer_affinity_score": 0.5,
            "customer_buying_confidence": 0.5,
            "discount_dependence_score": 0.5,
            "preferred_category": None,
        }

    def get_customer(
        self,
        customer_id: Optional[int],
        session_id: Optional[str] = None,
    ):

        if customer_id is None:
            return self._anonymous_profile()

        row = self.repository.get_by_customer_id(int(customer_id))

        if row is None:
            return self._anonymous_profile()

        preferred_categories = row.get("preferred_categories") or row.get("preferred_category")
        if isinstance(preferred_categories, str):
            preferred_categories = [preferred_categories]
        elif isinstance(preferred_categories, (list, tuple)):
            preferred_categories = list(preferred_categories)
        else:
            preferred_categories = []

        lifetime_value = float(row.get("lifetime_value") or row.get("customer_revenue") or 0.0)
        purchase_count = int(row.get("purchase_count") or row.get("customer_purchases") or 0)
        average_discount_taken = float(row.get("average_discount_taken") or row.get("customer_avg_discount") or 0.0)
        affinity_score = float(row.get("affinity_score") or row.get("customer_affinity_score") or 0.5)
        discount_dependence = float(row.get("discount_dependence") or row.get("discount_dependence_score") or 0.5)
        risk_profile = row.get("risk_profile") or ("low" if purchase_count <= 3 else "medium")

        profile = {
            "customer_id": int(row.get("customer_id", customer_id)),
            "is_known": True,
            "lifetime_value": round(lifetime_value, 2),
            "purchase_count": purchase_count,
            "average_discount_taken": round(average_discount_taken, 2),
            "affinity_score": round(max(0.0, min(1.0, affinity_score)), 4),
            "discount_dependence": round(max(0.0, min(1.0, discount_dependence)), 4),
            "risk_profile": risk_profile,
            "preferred_categories": preferred_categories,
            "customer_affinity_score": round(max(0.0, min(1.0, affinity_score)), 4),
            "customer_buying_confidence": float(row.get("customer_buying_confidence", 0.5)),
            "discount_dependence_score": round(max(0.0, min(1.0, discount_dependence)), 4),
            "preferred_category": preferred_categories[0] if preferred_categories else None,
        }

        return profile

    def minmax(self, series):
        minimum = series.min()
        maximum = series.max()

        if minimum == maximum:
            return pd.Series(0.5, index=series.index)

        return (series - minimum) / (maximum - minimum)

    def update_customer_affinity_score(self):
        self.customers["customer_affinity_score"] = (
            0.30 * self.minmax(self.customers["customer_purchase_rate"])
            + 0.25 * self.minmax(self.customers["customer_revenue"])
            + 0.15 * self.minmax(self.customers["customer_cart_rate"])
            + 0.15 * self.minmax(self.customers["customer_avg_engagement"])
            + 0.15 * self.minmax(self.customers["customer_avg_cart_intent"])
        )

    def update_customer_buying_confidence(self):
        self.customers["customer_buying_confidence"] = (
            0.60 * self.customers["customer_purchase_rate"]
            + 0.40 * (1 - self.customers["customer_abandonment_rate"])
        )

    def update_customer_discount_dependence_score(self):
        self.customers["discount_dependence_score"] = self.minmax(
            self.customers["customer_avg_discount"]
        )


def main():

    context = CustomerContext()

    test_customer_id = 5176

    result = context.get_customer(
        test_customer_id
    )

    print("=" * 80)
    print("CUSTOMER CONTEXT TEST")
    print("=" * 80)

    print(result)


if __name__ == "__main__":
    main()