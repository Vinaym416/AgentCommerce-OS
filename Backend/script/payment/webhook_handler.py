"""
AGENTCOMMERCE OS
PHASE 08C — RAZORPAY WEBHOOK HANDLER

Responsible only for:

1. Receiving Razorpay webhook payloads.
2. Verifying the webhook signature.
3. Validating supported events.
4. Extracting payment/order information.
5. Detecting duplicate webhook events.

The Webhook Handler does NOT:
- create Razorpay orders
- process payments
- create internal commerce orders
- perform business decisions

Flow:

Razorpay
    ↓
Webhook HTTP Request
    ↓
Webhook Handler
    ↓
Signature Verification
    ↓
Event Validation
    ↓
Payment Event Result
    ↓
Commerce Application
"""

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# WEBHOOK RESULT
# ============================================================

@dataclass
class WebhookResult:

    status: str

    valid: bool

    event: Optional[str]

    event_id: Optional[str]

    razorpay_payment_id: Optional[str]

    razorpay_order_id: Optional[str]

    payment_status: Optional[str]

    reason: str


# ============================================================
# WEBHOOK HANDLER
# ============================================================

class RazorpayWebhookHandler:

    SUPPORTED_EVENTS = {
        "payment.captured",
        "payment.failed",
        "order.paid",
    }

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
    ):
        load_dotenv()
        self.webhook_secret = (
            webhook_secret
            if webhook_secret is not None
            else os.getenv("RAZORPAY_WEBHOOK_SECRET")
        )

        print(
            "Razorpay Webhook Handler initialized."
        )

    # ========================================================
    # HANDLE WEBHOOK
    # ========================================================

    def handle(
        self,
        raw_body: str,
        signature: Optional[str],
        event_id: Optional[str] = None,
    ) -> WebhookResult:

        # ----------------------------------------------------
        # SECRET VALIDATION
        # ----------------------------------------------------

        if not self.webhook_secret:

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="webhook_secret_missing",
            )

        # ----------------------------------------------------
        # SIGNATURE VALIDATION
        # ----------------------------------------------------

        if not signature:

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="webhook_signature_missing",
            )

        if not isinstance(raw_body, str):

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="raw_webhook_body_required",
            )

        expected_signature = hmac.new(

            self.webhook_secret.encode("utf-8"),

            raw_body.encode("utf-8"),

            hashlib.sha256

        ).hexdigest()

        if not hmac.compare_digest(
            expected_signature,
            signature,
        ):

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="invalid_webhook_signature",
            )

        # ----------------------------------------------------
        # PARSE PAYLOAD
        # ----------------------------------------------------

        try:

            payload = json.loads(raw_body)

        except (json.JSONDecodeError, TypeError):

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="invalid_webhook_payload",
            )

        # ----------------------------------------------------
        # EVENT
        # ----------------------------------------------------

        event = payload.get("event")

        if not event:

            return WebhookResult(

                status="WEBHOOK_REJECTED",

                valid=False,

                event=None,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="webhook_event_missing",
            )

        # ----------------------------------------------------
        # SUPPORTED EVENT
        # ----------------------------------------------------

        if event not in self.SUPPORTED_EVENTS:

            return WebhookResult(

                status="WEBHOOK_IGNORED",

                valid=True,

                event=event,

                event_id=event_id,

                razorpay_payment_id=None,

                razorpay_order_id=None,

                payment_status=None,

                reason="unsupported_webhook_event",
            )

        # ----------------------------------------------------
        # DUPLICATE EVENT HANDLING IS DEFERRED TO THE
        # APPLICATION / MONGODB REPOSITORY LAYER.
        # ----------------------------------------------------

        # ----------------------------------------------------
        # EXTRACT PAYMENT / ORDER ENTITY
        # ----------------------------------------------------

        payment_entity = self._extract_entity(
            payload,
            "payment"
        )

        order_entity = self._extract_entity(
            payload,
            "order"
        )

        razorpay_payment_id = None

        razorpay_order_id = None

        payment_status = None

        if payment_entity:

            razorpay_payment_id = (
                payment_entity.get("id")
            )

            razorpay_order_id = (
                payment_entity.get("order_id")
            )

            payment_status = (
                payment_entity.get("status")
            )

        if order_entity:

            if razorpay_order_id is None:

                razorpay_order_id = (
                    order_entity.get("id")
                )

            if payment_status is None:

                if event == "order.paid":

                    payment_status = "paid"

        # ----------------------------------------------------
        # EVENT STATUS
        # ----------------------------------------------------

        if event == "payment.captured":

            payment_status = (
                payment_status
                or
                "captured"
            )

        elif event == "payment.failed":

            payment_status = (
                payment_status
                or
                "failed"
            )

        elif event == "order.paid":

            payment_status = (
                payment_status
                or
                "paid"
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return WebhookResult(

            status="WEBHOOK_ACCEPTED",

            valid=True,

            event=event,

            event_id=event_id,

            razorpay_payment_id=(
                razorpay_payment_id
            ),

            razorpay_order_id=(
                razorpay_order_id
            ),

            payment_status=payment_status,

            reason="webhook_verified_successfully",
        )

    # ========================================================
    # EXTRACT ENTITY
    # ========================================================

    def _extract_entity(
        self,
        payload: Dict[str, Any],
        entity_name: str,
    ) -> Optional[Dict[str, Any]]:

        payload_data = payload.get(
            "payload",
            {}
        )

        entity_data = payload_data.get(
            entity_name,
            {}
        )

        entity = entity_data.get(
            "entity"
        )

        if isinstance(entity, dict):

            return entity

        return None


# ============================================================
# SIGNATURE HELPER
# ============================================================

def generate_test_signature(
    raw_body: str,
    webhook_secret: str,
) -> str:

    """
    Test helper only.

    Generates the same HMAC-SHA256 signature
    used by Razorpay for webhook validation.
    """

    return hmac.new(

        webhook_secret.encode("utf-8"),

        raw_body.encode("utf-8"),

        hashlib.sha256

    ).hexdigest()


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — RAZORPAY WEBHOOK HANDLER"
    )

    print("=" * 80)

    secret = "TEST_WEBHOOK_SECRET"

    handler = RazorpayWebhookHandler(
        webhook_secret=secret
    )

    payload = {

        "entity": "event",

        "event": "payment.captured",

        "payload": {

            "payment": {

                "entity": {

                    "id": "pay_TEST456",

                    "order_id": "order_TEST123",

                    "status": "captured"

                }

            }

        }

    }

    raw_body = json.dumps(
        payload,
        separators=(",", ":")
    )

    signature = generate_test_signature(
        raw_body,
        secret
    )

    print("\n")
    print("-" * 80)
    print("TEST — VALID WEBHOOK")
    print("-" * 80)

    result = handler.handle(

        raw_body=raw_body,

        signature=signature,

        event_id="evt_TEST001"

    )

    print(result)

    print("\n")
    print("-" * 80)
    print("TEST — INVALID SIGNATURE")
    print("-" * 80)

    result = handler.handle(

        raw_body=raw_body,

        signature="INVALID_SIGNATURE",

        event_id="evt_TEST002"

    )

    print(result)


if __name__ == "__main__":

    main()