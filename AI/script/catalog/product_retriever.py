import os
import pandas as pd


# ============================================================
# AGENTCOMMERCE OS — PRODUCT RETRIEVER
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

CATALOG_FILE = os.path.join(
    BASE_DIR,
    "data",
    "catalog",
    "product_catalog.csv"
)


class ProductRetriever:

    def __init__(self, catalog_file=CATALOG_FILE):

        self.catalog = pd.read_csv(catalog_file)

    # --------------------------------------------------------
    # Retrieve products
    # --------------------------------------------------------

    def search(
        self,
        budget=None,
        category=None,
        min_rating=None,
        limit=5
    ):

        df = self.catalog.copy()

        # Budget filter
        if budget is not None:

            df = df[
                df["current_price"] <= budget
            ]

        # Category filter
        if category is not None:

            df = df[
                df["product_category"] == category
            ]

        # Rating filter
        if min_rating is not None:

            df = df[
                df["avg_rating"] >= min_rating
            ]

        # ----------------------------------------------------
        # Ranking
        # ----------------------------------------------------

        if len(df) > 0:

            df["retrieval_score"] = (
                df["product_score"] * 0.50
                +
                df["conversion_rate"] * 0.25
                +
                df["quality_score"] * 0.25
            )

            df = df.sort_values(
                "retrieval_score",
                ascending=False
            )

        return df.head(limit)

    # --------------------------------------------------------
    # Display results
    # --------------------------------------------------------

    def display(self, results):

        if len(results) == 0:

            print("No matching products found.")

            return

        print()
        print("=" * 80)
        print("PRODUCT RECOMMENDATIONS")
        print("=" * 80)

        for _, product in results.iterrows():

            print()
            print(
                f"Product ID       : "
                f"{int(product['product_id'])}"
            )

            print(
                f"Category         : "
                f"{product['category_name']}"
            )

            print(
                f"Price            : "
                f"₹{product['current_price']:.2f}"
            )

            print(
                f"Rating           : "
                f"{product['avg_rating']:.2f}/5"
            )

            print(
                f"Conversion Rate  : "
                f"{product['conversion_rate']:.2%}"
            )

            print(
                f"Demand Score     : "
                f"{product['demand_score']:.3f}"
            )

            print(
                f"Product Score    : "
                f"{product['product_score']:.3f}"
            )


# ============================================================
# TEST
# ============================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS — PRODUCT RETRIEVER")
    print("=" * 80)

    retriever = ProductRetriever()

    print()
    print("QUERY")
    print("-" * 80)

    print("Find products under ₹2000")

    results = retriever.search(
        budget=2000,
        limit=5
    )

    retriever.display(results)

    print()
    print("=" * 80)
    print("RETRIEVER TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()