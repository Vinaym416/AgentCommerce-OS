import pandas as pd

from script.database.repositories.product_repository import ProductRepository

# ============================================================
# AGENTCOMMERCE OS — PRODUCT RETRIEVER
# ============================================================

class ProductRetriever:

    def __init__(self, repository=None):
        self.repository = repository or ProductRepository()

    @staticmethod
    def _normalize_product_row(row):
        price = float(row.get("current_price") or row.get("price") or 0.0)
        cost_price = row.get("cost_price")
        if cost_price is None:
            cost_price = row.get("base_cost") or row.get("cost") or (price * 0.6)
        cost_price = float(cost_price)

        popularity = row.get("popularity_score")
        if popularity is None:
            popularity = row.get("product_score") or row.get("demand_score") or row.get("conversion_rate") or 0.0

        margin_percent = 0.0
        if price > 0:
            margin_percent = ((price - cost_price) / price) * 100

        category = row.get("category") or row.get("product_category") or row.get("category_name") or "general"

        return {
            "product_id": int(row.get("product_id")),
            "name": row.get("name") or row.get("product_name") or f"Product {row.get('product_id')}",
            "price": round(price, 2),
            "cost_price": round(cost_price, 2),
            "stock_quantity": int(row.get("stock_quantity") or row.get("stock") or row.get("inventory") or 0),
            "category": category,
            "margin_percent": round(float(margin_percent), 2),
            "popularity_score": round(float(popularity), 4),
        }

    # --------------------------------------------------------
    # Retrieve products
    # --------------------------------------------------------

    def search(
        self,
        intent=None,
        customer_context=None,
        limit=5,
        budget=None,
        min_budget=None,
        category=None,
        min_rating=None,
    ):
        if isinstance(intent, dict):
            budget = intent.get("budget_max") or intent.get("budget") or budget
            min_budget = intent.get("budget_min") or min_budget
            category = intent.get("product_category") or category
        elif intent is not None:
            budget = getattr(intent, "budget", None) or budget
            min_budget = getattr(intent, "budget_min", None) or min_budget
            category = getattr(intent, "product_category", None) or category

        if str(category or "").strip().lower() in {
            "",
            "general",
            "unspecified",
            "unknown",
            "null",
            "none",
        }:
            category = None

        if isinstance(customer_context, dict):
            customer_categories = customer_context.get("preferred_categories") or []
            if category is None and customer_categories:
                category = customer_categories[0]

        products = self.repository.search(
            budget=budget,
            min_budget=min_budget,
            category=category,
            min_rating=min_rating,
            limit=limit,
        )

        normalized = [self._normalize_product_row(row) for row in products]
        product_preferences = (
            intent.get("product_preferences")
            if isinstance(intent, dict)
            else getattr(intent, "product_preferences", [])
        )
        if "low_price" in (product_preferences or []):
            normalized.sort(key=lambda product: product["price"])
        return normalized

    def get_by_product_id(self, product_id):
        """Retrieve one product without applying recommendation ranking."""
        row = self.repository.get_by_product_id(int(product_id))
        return self._normalize_product_row(row) if row is not None else None

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

        for product in results:

            print()
            print(
                f"Product ID       : "
                f"{int(product['product_id'])}"
            )

            print(
                f"Category         : "
                f"{product['category']}"
            )

            print(
                f"Price            : "
                f"₹{product['price']:.2f}"
            )

            print(
                f"Margin %         : "
                f"{product['margin_percent']:.2f}%"
            )

            print(
                f"Popularity Score : "
                f"{product['popularity_score']:.3f}"
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