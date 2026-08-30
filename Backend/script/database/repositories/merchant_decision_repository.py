"""MongoDB persistence for merchant decisions."""

from typing import Any, Dict

from script.database.mongodb import get_database


class MerchantDecisionRepository:

    def __init__(self):
        self.collection = get_database()["merchant_decisions"]

    @staticmethod
    def _seed_key(decision: Dict[str, Any]) -> str:
        product_id = decision.get("product_id")
        if product_id is not None:
            return f"merchant_decision:product:{product_id}"
        return "merchant_decision:unknown"

    def create(self, decision: Dict[str, Any]):
        document = dict(decision)
        document.setdefault("_seed_id", self._seed_key(document))

        return self.collection.update_one(
            {"_seed_id": document["_seed_id"]},
            {"$set": document},
            upsert=True,
        )
