"""MongoDB persistence for payments."""

from typing import Any, Dict
from uuid import uuid4
from datetime import datetime, timezone

from script.database.mongodb import get_database


class PaymentRepository:

	def __init__(self):
		self.collection = get_database()["payments"]

	def create(self, payment: Dict[str, Any] = None, **fields):
		payment = dict(payment or {})
		payment.update(fields)
		payment.setdefault("transaction_id", "TXN-" + uuid4().hex[:12].upper())
		payment.setdefault("created_at", datetime.now(timezone.utc).isoformat())
		return self.collection.insert_one(payment)
