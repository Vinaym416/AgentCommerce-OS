import pandas as pd

from script.database.repositories.product_repository import ProductRepository

# ============================================================
# AGENTCOMMERCE OS — PRODUCT RETRIEVER
# ============================================================

class ProductRetriever:

    def __init__(self, repository=None):
        self.repository = repository or ProductRepository()

    # --------------------------------------------------------
    # Retrieve products
    # --------------------------------------------------------

    def search(
        self,
        budget=None,
        category=None,
        min_rating=None,
        limit=None
    ):

        products = self.repository.search(
            budget=budget,
            category=category,
            min_rating=min_rating,
            limit=limit,
        )

        return pd.DataFrame(products)

    def get_by_product_id(self, product_id):
        """Retrieve one product without applying recommendation ranking."""
        return self.repository.get_by_product_id(int(product_id))

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