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

    def get_customer(
        self,
        customer_id: Optional[int]
    ):

        if customer_id is None:
            return None

        row = self.repository.get_by_customer_id(int(customer_id))

        if row is None:
            return None

        return {
            "customer_id": int(row["customer_id"]),

            "sessions": int(row.get("customer_sessions", 0)),

            "purchases": int(row.get("customer_purchases", 0)),

            "revenue": float(row.get("customer_revenue", 0)),

            "average_order_value": float(row.get("customer_avg_order_value", 0)),

            "average_discount": float(row.get("customer_avg_discount", 0)),

            "purchase_rate": float(row.get("customer_purchase_rate", 0)),

            "cart_rate": float(row.get("customer_cart_rate", 0)),

            "abandonment_rate": float(row.get("customer_abandonment_rate", 0)),

            "average_session_time": float(row.get("customer_avg_session_time", 0)),

            "average_pages": float(row.get("customer_avg_pages", 0)),

            "preferred_category": row.get("preferred_category"),

            "customer_affinity_score": float(row.get("customer_affinity_score", 0.5)),

            "customer_buying_confidence": float(row.get("customer_buying_confidence", 0.5)),

            "discount_dependence_score": float(row.get("discount_dependence_score", 0.25))
        }

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