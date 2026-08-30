"""MongoDB access for catalog products."""

from typing import Any, Dict, List, Optional

from script.database.mongodb import get_database


class ProductRepository:

    def __init__(self):
        self.collection = get_database()["products"]

    def search(
        self,
        budget: Optional[float] = None,
        category: Optional[Any] = None,
        min_rating: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}

        if budget is not None:
            query["current_price"] = {"$lte": float(budget)}

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

        return list(cursor)

    def get_by_product_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        return self.collection.find_one(
            {"product_id": int(product_id)},
            {"_id": 0},
        )
