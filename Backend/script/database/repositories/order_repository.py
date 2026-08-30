"""
AGENTCOMMERCE OS
ORDER REPOSITORY

Persistent MongoDB storage for internal commerce orders.

Responsibilities:
- Create orders
- Find orders
- Enforce payment-level idempotency
- Update order status
"""

from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from script.database.mongodb import get_database


class OrderRepository:

    def __init__(self):

        self.collection = get_database()["orders"]

        # ----------------------------------------------------
        # IDEMPOTENCY
        # ----------------------------------------------------

        self.collection.create_index(
            "payment_transaction_id",
            unique=True,
            sparse=True,
            name="unique_payment_transaction_id",
        )

    # ========================================================
    # CREATE
    # ========================================================

    def create(
        self,
        order: Optional[Dict[str, Any]] = None,
        **fields,
    ):

        order = dict(order or {})

        order.update(fields)

        order.setdefault(
            "order_id",
            "ORD-" + uuid4().hex[:10].upper(),
        )

        order.setdefault(
            "created_at",
            datetime.now(
                timezone.utc
            ).isoformat(),
        )

        try:

            result = self.collection.insert_one(
                order
            )

            return {
                "created": True,
                "duplicate": False,
                "order_id": order["order_id"],
                "document_id": str(
                    result.inserted_id
                ),
            }

        except DuplicateKeyError:

            existing = (
                self.find_by_payment_transaction_id(
                    order.get(
                        "payment_transaction_id"
                    )
                )
            )

            return {
                "created": False,
                "duplicate": True,
                "order_id": (
                    existing.get("order_id")
                    if existing
                    else None
                ),
                "reason":
                    "order_already_exists_for_payment",
            }

    # ========================================================
    # FIND BY CUSTOMER
    # ========================================================

    def find_by_customer_id(
        self,
        customer_id: int,
    ):

        return list(
            self.collection.find(
                {
                    "customer_id":
                        int(customer_id)
                },
                {
                    "_id": 0
                },
            )
        )

    # ========================================================
    # FIND BY PAYMENT TRANSACTION
    # ========================================================

    def find_by_payment_transaction_id(
        self,
        payment_transaction_id: str,
    ):

        if not payment_transaction_id:
            return None

        return self.collection.find_one(
            {
                "payment_transaction_id":
                    payment_transaction_id
            },
            {
                "_id": 0
            },
        )

    # ========================================================
    # FIND BY ORDER ID
    # ========================================================

    def find_by_order_id(
        self,
        order_id: str,
    ):

        return self.collection.find_one(
            {
                "order_id": order_id
            },
            {
                "_id": 0
            },
        )

    # ========================================================
    # FIND BY RAZORPAY PAYMENT ID
    # ========================================================

    def find_by_razorpay_payment_id(
        self,
        razorpay_payment_id: str,
    ):

        if not razorpay_payment_id:
            return None

        return self.collection.find_one(
            {
                "razorpay_payment_id":
                    razorpay_payment_id
            },
            {
                "_id": 0
            },
        )

    # ========================================================
    # UPDATE STATUS
    # ========================================================

    def update_status(
        self,
        order_id: str,
        status: str,
    ):

        return self.collection.update_one(
            {
                "order_id": order_id
            },
            {
                "$set": {
                    "status": status,
                    "updated_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                }
            },
        )