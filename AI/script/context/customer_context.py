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


ROOT = Path(__file__).resolve().parents[2]

CUSTOMER_FEATURES = (
    ROOT
    / "data"
    / "features"
    / "customer_features.csv"
)


class CustomerContext:

    def __init__(
        self,
        customer_file=CUSTOMER_FEATURES
    ):

        self.customers = pd.read_csv(customer_file)

        self.customers["customer_id"] = (
            self.customers["customer_id"].astype(int)
        )

        self.update_customer_affinity_score()
        self.update_customer_buying_confidence()
        self.update_customer_discount_dependence_score()

    def get_customer(
        self,
        customer_id: Optional[int]
    ):

        if customer_id is None:
            return None

        matches = self.customers[
            self.customers["customer_id"] == int(customer_id)
        ]

        if matches.empty:
            return None

        row = matches.iloc[0]

        return {
            "customer_id": int(
                row["customer_id"]
            ),

            "sessions": int(
                row["customer_sessions"]
            ),

            "purchases": int(
                row["customer_purchases"]
            ),

            "revenue": float(
                row["customer_revenue"]
            ),

            "average_order_value": float(
                row["customer_avg_order_value"]
            ),

            "average_discount": float(
                row["customer_avg_discount"]
            ),

            "purchase_rate": float(
                row["customer_purchase_rate"]
            ),

            "cart_rate": float(
                row["customer_cart_rate"]
            ),

            "abandonment_rate": float(
                row["customer_abandonment_rate"]
            ),

            "average_session_time": float(
                row["customer_avg_session_time"]
            ),

            "average_pages": float(
                row["customer_avg_pages"]
            ),

            "preferred_category": (
                None
                if pd.isna(
                    row["preferred_category"]
                )
                else int(
                    row["preferred_category"]
                )
            ),

            "customer_affinity_score": float(
                row["customer_affinity_score"]
            ),

            "customer_buying_confidence": float(
                row["customer_buying_confidence"]
            ),

            "discount_dependence_score": float(
                row["discount_dependence_score"]
            )
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