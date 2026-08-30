"""
AGENTCOMMERCE OS
WEBHOOK REPOSITORY

Responsible for persistent Razorpay webhook event storage
and duplicate-event detection.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from script.database.mongodb import get_database


class WebhookRepository:

    def __init__(self):

        self.collection = get_database()["webhook_events"]

        # ----------------------------------------------------
        # UNIQUE INDEX
        # ----------------------------------------------------

        self.collection.create_index(
            "event_id",
            unique=True,
            name="unique_webhook_event_id",
        )

    # ========================================================
    # CREATE EVENT
    # ========================================================

    def create(
        self,
        event_id: str,
        event: Optional[str] = None,
        event_type: Optional[str] = None,
        razorpay_payment_id: Optional[str] = None,
        razorpay_order_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        order_id: Optional[str] = None,
        payment_status: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        resolved_event_type = event_type or event or "unknown"
        resolved_payment_id = payment_id or razorpay_payment_id
        resolved_order_id = order_id or razorpay_order_id
        received_at = datetime.now(timezone.utc).isoformat()

        document = {
            "event_id": event_id,
            "event": resolved_event_type,
            "event_type": resolved_event_type,
            "payment_id": resolved_payment_id,
            "order_id": resolved_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "payment_status": payment_status,
            "raw_payload": raw_payload,
            "processed": False,
            "status": "RECEIVED",
            "received_at": received_at,
            "processed_at": None,
            "created_at": received_at,
        }

        try:

            result = self.collection.insert_one(
                document
            )

            return {
                "created": True,
                "duplicate": False,
                "event_id": event_id,
                "event_type": resolved_event_type,
                "document_id": str(result.inserted_id),
                "status": "RECEIVED",
            }

        except DuplicateKeyError:

            return {
                "created": False,
                "duplicate": True,
                "event_id": event_id,
                "event_type": resolved_event_type,
                "reason": "webhook_event_already_exists",
                "status": "DUPLICATE",
            }

    # ========================================================
    # MARK AS PROCESSED
    # ========================================================

    def mark_processed(
        self,
        event_id: str,
        *,
        status: str = "PROCESSED",
    ) -> Dict[str, Any]:

        now = datetime.now(timezone.utc).isoformat()
        updated = self.collection.update_one(
            {"event_id": event_id},
            {
                "$set": {
                    "processed": True,
                    "status": status,
                    "processed_at": now,
                }
            },
        )

        return {
            "updated": updated.modified_count > 0,
            "event_id": event_id,
            "status": status,
            "processed_at": now,
        }

    # ========================================================
    # FIND EVENT
    # ========================================================

    def find_by_event_id(
        self,
        event_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.collection.find_one(
            {
                "event_id": event_id
            },
            {
                "_id": 0
            },
        )

    # ========================================================
    # CHECK DUPLICATE
    # ========================================================

    def exists(
        self,
        event_id: str,
    ) -> bool:

        return (
            self.collection.count_documents(
                {
                    "event_id": event_id
                },
                limit=1,
            )
            > 0
        )