"""MongoDB persistence for orders."""

from typing import Any, Dict
from uuid import uuid4
from datetime import datetime, timezone

from script.database.mongodb import get_database


class OrderRepository:

	def __init__(self):
		self.collection = get_database()["orders"]

	def create(self, order: Dict[str, Any] = None, **fields):
		order = dict(order or {})
		order.update(fields)
		order.setdefault("order_id", "ORD-" + uuid4().hex[:10].upper())
		order.setdefault("created_at", datetime.now(timezone.utc).isoformat())
		return self.collection.insert_one(order)

	def find_by_customer_id(self, customer_id: int):
		return list(self.collection.find({"customer_id": int(customer_id)}, {"_id": 0}))
