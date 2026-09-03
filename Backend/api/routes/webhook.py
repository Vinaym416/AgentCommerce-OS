"""
AGENTCOMMERCE OS
PHASE 08G — RAZORPAY WEBHOOK ROUTE

Receives Razorpay webhook HTTP requests.

Flow:

Razorpay
    ↓
POST /webhooks/razorpay
    ↓
Raw request body
    ↓
Signature verification
    ↓
Event ID extraction
    ↓
WebhookService
    ↓
MongoDB persistence
"""

import json
from functools import lru_cache

from fastapi import APIRouter, Header, HTTPException, Request

from script.payment.webhook_handler import (
    RazorpayWebhookHandler,
)

from script.webhook.webhook_service import (
    WebhookService,
)


router = APIRouter()


# ============================================================
# WEBHOOK HANDLER + SERVICE
# ============================================================

webhook_handler = RazorpayWebhookHandler()


@lru_cache(maxsize=1)
def get_webhook_service() -> WebhookService:
    return WebhookService()


# ============================================================
# RAZORPAY WEBHOOK
# ============================================================

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,

    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),

    x_razorpay_event_id: str | None = Header(
        default=None,
        alias="x-razorpay-event-id",
    ),
):

    # --------------------------------------------------------
    # READ RAW BODY
    # --------------------------------------------------------

    raw_body = await request.body()

    raw_body_string = raw_body.decode(
        "utf-8"
    )

    # --------------------------------------------------------
    # VERIFY + PARSE WEBHOOK
    # --------------------------------------------------------

    webhook_result = webhook_handler.handle(

        raw_body=raw_body_string,

        signature=x_razorpay_signature,

        event_id=x_razorpay_event_id,
    )

    # --------------------------------------------------------
    # REJECT INVALID WEBHOOK
    # --------------------------------------------------------

    if not webhook_result.valid:

        raise HTTPException(
            status_code=400,
            detail={
                "status": webhook_result.status,
                "reason": webhook_result.reason,
            },
        )

    # --------------------------------------------------------
    # PARSE PAYLOAD FOR PERSISTENCE
    # --------------------------------------------------------

    try:

        raw_payload = json.loads(
            raw_body_string
        )

    except json.JSONDecodeError:

        return {

            "success": False,

            "status": "WEBHOOK_REJECTED",

            "reason": "invalid_webhook_payload",

        }

    # --------------------------------------------------------
    # PROCESS VERIFIED WEBHOOK
    # --------------------------------------------------------

    result = get_webhook_service().process(

        webhook_result=webhook_result,

        raw_payload=raw_payload,

    )

    return result