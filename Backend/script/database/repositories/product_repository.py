"""MongoDB access for catalog products."""

from typing import Any, Dict, List, Optional

from script.database.mongodb import get_database


class ProductRepository:

    def __init__(self):
        self.collection = get_database()["products"]

    def search(
        self,
        budget: Optional[float] = None,
        min_budget: Optional[float] = None,
        category: Optional[Any] = None,
        min_rating: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}

        if budget is not None or min_budget is not None:
            price_filter: Dict[str, float] = {}
            if min_budget is not None:
                price_filter["$gte"] = float(min_budget)
            if budget is not None:
                price_filter["$lte"] = float(budget)
            query["current_price"] = price_filter

        normalized_category = str(category or "").strip().lower()
        if normalized_category in {"", "any", "all", "general", "unspecified", "unknown", "none", "null"}:
            category = None

        if category is not None:
            query["$or"] = [
                {"product_category": category},
                {"category_name": category},
            ]

        if min_rating is not None:
            query["avg_rating"] = {"$gte": float(min_rating)}

        cursor = self.collection.find(query, {"_id": 0}).sort(
            [
                ("product_score", -1),
                ("conversion_rate", -1),
                ("quality_score", -1),
            ]
        )

        if limit is not None:
            cursor = cursor.limit(limit)

        results = list(cursor)

        # The catalog currently stores generated category labels such as
        # "Category 1", while buyer intents contain human labels such as
        # "running shoes". Keep the price constraint and relax only the
        # unmatched category so valid products are still returned.
        if not results and category is not None:
            fallback_query = dict(query)
            fallback_query.pop("$or", None)
            fallback_cursor = self.collection.find(
                fallback_query,
                {"_id": 0},
            ).sort(
                [
                    ("product_score", -1),
                    ("conversion_rate", -1),
                    ("quality_score", -1),
                ]
            )
            if limit is not None:
                fallback_cursor = fallback_cursor.limit(limit)
            results = list(fallback_cursor)

        return results

    def get_by_product_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        return self.collection.find_one(
            {"product_id": int(product_id)},
            {"_id": 0},
        )
