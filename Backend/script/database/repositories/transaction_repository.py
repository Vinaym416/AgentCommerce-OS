"""
AGENTCOMMERCE OS
TRANSACTION REPOSITORY

Persistent MongoDB storage for commerce transactions.

A transaction connects:

Customer
    ↓
Product
    ↓
Negotiated Price
    ↓
Checkout
    ↓
Razorpay
    ↓
Payment
    ↓
Internal Order
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError, OperationFailure

from script.database.mongodb import get_database


class TransactionRepository:

    def __init__(self):

        self.collection = get_database()[
            "transactions"
        ]

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        self._safe_create_index(
            "customer_id",
            name="transaction_customer_id",
        )

        self._safe_create_index(
            "transaction_id",
            unique=True,
            name="unique_transaction_id",
        )

        self._safe_create_index(
            "payment_transaction_id",
            unique=True,
            sparse=True,
            name="unique_payment_transaction_id",
        )

        self._safe_create_index(
            "razorpay_order_id",
            unique=True,
            sparse=True,
            name="unique_razorpay_order_id",
        )

        self._safe_create_index(
            "razorpay_payment_id",
            unique=True,
            sparse=True,
            name="unique_razorpay_payment_id",
        )

        self._purge_null_unique_fields()

    def _safe_create_index(self, keys, **kwargs):
        try:
            self.collection.create_index(keys, **kwargs)
        except (DuplicateKeyError, OperationFailure) as exc:
            detail = getattr(exc, "details", {}) or {}
            code = detail.get("code")
            message = str(exc).lower()
            if code == 85 or "already exists" in message or "different name" in message:
                return
            raise

    @staticmethod
    def _sanitize_optional_fields(document: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = dict(document)
        for key in (
            "payment_transaction_id",
            "razorpay_payment_id",
            "razorpay_order_id",
        ):
            if cleaned.get(key) is None:
                cleaned.pop(key, None)
        return cleaned

    def _purge_null_unique_fields(self):
        for field in (
            "payment_transaction_id",
            "razorpay_order_id",
            "razorpay_payment_id",
        ):
            self.collection.update_many(
                {field: None},
                {"$unset": {field: ""}},
            )

    # ========================================================
    # CREATE / UPSERT
    # ========================================================

    def upsert(
        self,
        transaction: Dict[str, Any],
    ) -> Dict[str, Any]:

        transaction = self._sanitize_optional_fields(
            dict(transaction)
        )

        transaction_id = transaction.get(
            "transaction_id"
        )

        if not transaction_id:

            raise ValueError(
                "transaction_id is required"
            )

        transaction["updated_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
        transaction.setdefault(
            "created_at",
            datetime.now(timezone.utc).isoformat(),
        )

        existing_by_transaction = self.collection.find_one(
            {"transaction_id": transaction_id}
        )
        if existing_by_transaction is not None:
            merged = {**existing_by_transaction, **transaction}
            self.collection.update_one(
                {"_id": existing_by_transaction["_id"]},
                {"$set": merged},
            )
            return {
                "success": True,
                "transaction_id": transaction_id,
                "created": False,
                "modified": True,
            }

        for key in (
            "razorpay_order_id",
            "razorpay_payment_id",
            "payment_transaction_id",
        ):
            value = transaction.get(key)
            if not value:
                continue
            existing_by_unique = self.collection.find_one({key: value})
            if existing_by_unique is not None:
                merged = {**existing_by_unique, **transaction}
                merged["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.collection.update_one(
                    {"_id": existing_by_unique["_id"]},
                    {"$set": merged},
                )
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "created": False,
                    "modified": True,
                }

        result = self.collection.insert_one(transaction)
        return {
            "success": True,
            "transaction_id": transaction_id,
            "created": bool(result.inserted_id),
            "modified": False,
        }

    def _resolve_duplicate_query(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for key in (
            "transaction_id",
            "razorpay_order_id",
            "razorpay_payment_id",
            "payment_transaction_id",
        ):
            value = transaction.get(key)
            if value is not None:
                return {key: value}
        return None

    # ========================================================
    # GET BY CUSTOMER
    # ========================================================

    def get_by_customer_id(
        self,
        customer_id: int,
    ) -> Optional[Dict[str, Any]]:

        return self.collection.find_one(

            {
                "customer_id":
                    int(customer_id)
            },

            {
                "_id": 0
            },

            sort=[
                (
                    "updated_at",
                    -1
                )
            ],
        )

    # ========================================================
    # GET BY TRANSACTION ID
    # ========================================================

    def get_by_transaction_id(
        self,
        transaction_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.collection.find_one(

            {
                "transaction_id":
                    transaction_id
            },

            {
                "_id": 0
            },
        )

    # ========================================================
    # GET BY PAYMENT TRANSACTION ID
    # ========================================================

    def get_by_payment_transaction_id(
        self,
        payment_transaction_id: str,
    ) -> Optional[Dict[str, Any]]:

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
    # GET BY RAZORPAY ORDER ID
    # ========================================================

    def get_by_razorpay_order_id(
        self,
        razorpay_order_id: str,
    ) -> Optional[Dict[str, Any]]:

        if not razorpay_order_id:
            return None

        return self.collection.find_one(

            {
                "razorpay_order_id":
                    razorpay_order_id
            },

            {
                "_id": 0
            },
        )

    # ========================================================
    # GET BY RAZORPAY PAYMENT ID
    # ========================================================

    def get_by_razorpay_payment_id(
        self,
        razorpay_payment_id: str,
    ) -> Optional[Dict[str, Any]]:

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
    # UPDATE PAYMENT INFORMATION
    # ========================================================

    def update_payment(

        self,

        transaction_id: str,

        *,
        payment_transaction_id:
            Optional[str] = None,

        razorpay_payment_id:
            Optional[str] = None,

        razorpay_order_id:
            Optional[str] = None,

        payment_status:
            Optional[str] = None,

        status:
            Optional[str] = None,
    ):

        update_fields = {}

        if payment_transaction_id is not None:

            update_fields[
                "payment_transaction_id"
            ] = payment_transaction_id

        if razorpay_payment_id is not None:

            update_fields[
                "razorpay_payment_id"
            ] = razorpay_payment_id

        if razorpay_order_id is not None:

            update_fields[
                "razorpay_order_id"
            ] = razorpay_order_id

        if payment_status is not None:

            update_fields[
                "payment_status"
            ] = payment_status

        if status is not None:

            update_fields[
                "status"
            ] = status

        update_fields[
            "updated_at"
        ] = datetime.now(
            timezone.utc
        ).isoformat()

        return self.collection.update_one(

            {
                "transaction_id":
                    transaction_id
            },

            {
                "$set":
                    update_fields
            },
        )

    # ========================================================
    # UPDATE ORDER
    # ========================================================

    def update_order(

        self,

        transaction_id: str,

        order_id: str,

    ):

        return self.collection.update_one(

            {
                "transaction_id":
                    transaction_id
            },

            {
                "$set": {

                    "order_id":
                        order_id,

                    "status":
                        "ORDER_CREATED",

                    "updated_at":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                }
            },
        )