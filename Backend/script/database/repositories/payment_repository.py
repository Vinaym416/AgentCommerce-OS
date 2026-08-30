
"""
AGENTCOMMERCE OS
PAYMENT REPOSITORY

Responsible for persistent payment storage.

The repository does NOT:
- decide payment state
- validate webhook signatures
- call Razorpay
- make AI decisions
"""

from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from script.database.mongodb import get_database


class PaymentRepository:

    def __init__(self):

        self.collection = get_database()["payments"]

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        try:
            self.collection.create_index(
                "razorpay_payment_id",
                unique=True,
                sparse=True,
                name="unique_razorpay_payment_id",
            )
        except DuplicateKeyError:
            print(
                "PaymentRepository: unique razorpay_payment_id index build failed; existing duplicate records already present. Continuing without crashing startup."
            )

        try:
            self.collection.create_index(
                "razorpay_order_id",
                name="razorpay_order_id_index",
            )
        except DuplicateKeyError:
            print(
                "PaymentRepository: razorpay_order_id index already exists. Continuing."
            )

        try:
            self.collection.create_index(
                "transaction_id",
                name="transaction_id_index",
            )
        except DuplicateKeyError:
            print(
                "PaymentRepository: transaction_id index already exists. Continuing."
            )

    # ========================================================
    # CREATE
    # ========================================================

    def create(
        self,
        payment: Optional[Dict[str, Any]] = None,
        **fields,
    ):

        payment = dict(payment or {})

        payment.update(fields)

        for key in (
            "razorpay_payment_id",
            "razorpay_order_id",
            "transaction_id",
        ):
            if payment.get(key) is None:
                payment.pop(key, None)

        if not payment.get("transaction_id"):
            payment["transaction_id"] = (
                "TXN-" + uuid4().hex[:12].upper()
            )

        payment.setdefault(
            "created_at",
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        payment.setdefault(
            "updated_at",
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        return self.collection.insert_one(
            payment
        )

    # ========================================================
    # FIND BY RAZORPAY PAYMENT ID
    # ========================================================

    def find_by_razorpay_payment_id(
        self,
        razorpay_payment_id: str,
    ) -> Optional[Dict[str, Any]]:

        if not razorpay_payment_id:

            return None

        return self.collection.find_one(
            {
                "razorpay_payment_id":
                    razorpay_payment_id
            }
        )

    # ========================================================
    # FIND BY RAZORPAY ORDER ID
    # ========================================================

    def find_by_razorpay_order_id(
        self,
        razorpay_order_id: str,
    ) -> Optional[Dict[str, Any]]:

        if not razorpay_order_id:

            return None

        return self.collection.find_one(
            {
                "razorpay_order_id":
                    razorpay_order_id
            }
        )

    # ========================================================
    # UPDATE PAYMENT STATE
    # ========================================================

    def update_state(
        self,
        razorpay_payment_id: Optional[str],
        payment_state: str,
        event: Optional[str] = None,
        event_id: Optional[str] = None,
    ):

        if not razorpay_payment_id:

            return None

        update_fields = {

            "payment_state":
                payment_state,

            "updated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

        if event:

            update_fields[
                "last_event"
            ] = event

        if event_id:

            update_fields[
                "last_event_id"
            ] = event_id

        return self.collection.update_one(

            {
                "razorpay_payment_id":
                    razorpay_payment_id
            },

            {
                "$set":
                    update_fields
            },
        )

