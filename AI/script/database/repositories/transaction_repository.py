"""MongoDB persistence for transaction state."""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import uuid4

from script.database.mongodb import get_database


class TransactionRepository:

	def __init__(self):
		self.collection = get_database()["transactions"]

	def get_by_customer_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
		return self.collection.find_one(
			{"customer_id": int(customer_id)},
			{"_id": 0},
			sort=[("updated_at", -1)],
		)

	def upsert(self, transaction: Dict[str, Any]):
		return self.collection.update_one(
			{"transaction_id": transaction["transaction_id"]},
			{"$set": transaction},
			upsert=True,
		)

	def create(self, **fields):
		fields.setdefault(
			"transaction_id",
			"TRX-" + uuid4().hex[:12].upper(),
		)
		fields.setdefault(
			"updated_at",
			datetime.now(timezone.utc).isoformat(),
		)
		self.collection.insert_one(fields)
		return fields

	def create_or_update(self, customer_id: int, **fields):
		current = self.get_by_customer_id(customer_id)
		if current:
			fields["updated_at"] = datetime.now(timezone.utc).isoformat()
			self.collection.update_one(
				{"transaction_id": current["transaction_id"]},
				{"$set": fields},
			)
			current.update(fields)
			return current

		fields["customer_id"] = int(customer_id)
		return self.create(**fields)

	def update_status(self, customer_id: int, status: str):
		return self.update(customer_id, {"status": status})

	def update(self, customer_id: int, updates: Dict[str, Any]):
		current = self.get_by_customer_id(customer_id)
		if current is None:
			return None

		updates = dict(updates)
		updates["updated_at"] = datetime.now(timezone.utc).isoformat()
		self.collection.update_one(
			{"transaction_id": current["transaction_id"]},
			{"$set": updates},
		)
		current.update(updates)
		return current
