"""
AGENTCOMMERCE OS
END-TO-END WEBHOOK TEST

Tests:

Razorpay payload
    ↓
HMAC signature
    ↓
FastAPI webhook route
    ↓
WebhookHandler
    ↓
WebhookService
    ↓
WebhookRepository
    ↓
PaymentService
    ↓
PaymentStateMachine
    ↓
PaymentRepository
"""

import hashlib
import hmac
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

WEBHOOK_URL = (
    f"{BASE_URL}/webhooks/razorpay"
)

WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET",
    "AGENTCOMMERCE_WEBHOOK_SECRET_2026",
)


# ============================================================
# SIGNATURE
# ============================================================

def generate_signature(raw_body: str) -> str:

    return hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        raw_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ============================================================
# SEND WEBHOOK
# ============================================================

def send_webhook(
    payload: dict,
    event_id: str,
):

    raw_body = json.dumps(
        payload,
        separators=(",", ":"),
    )

    signature = generate_signature(
        raw_body
    )

    response = requests.post(
        WEBHOOK_URL,
        data=raw_body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
            "x-razorpay-event-id": event_id,
        },
    )

    print("\nHTTP STATUS:", response.status_code)

    try:
        print(
            json.dumps(
                response.json(),
                indent=2,
            )
        )

    except Exception:

        print(
            response.text
        )

    return response


# ============================================================
# PAYMENT CAPTURED PAYLOAD
# ============================================================

def captured_payload():

    return {

        "entity": "event",

        "event": "payment.captured",

        "payload": {

            "payment": {

                "entity": {

                    "id": "pay_TEST_E2E_001",

                    "order_id": "order_TEST_E2E_001",

                    "status": "captured",

                }

            }

        }

    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — WEBHOOK E2E TEST"
    )

    print("=" * 80)

    # ========================================================
    # TEST 1
    # NEW WEBHOOK
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 1 — NEW PAYMENT.CAPTURED WEBHOOK")
    print("-" * 80)

    send_webhook(
        payload=captured_payload(),
        event_id="evt_E2E_001",
    )

    # ========================================================
    # TEST 2
    # DUPLICATE
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 2 — DUPLICATE WEBHOOK")
    print("-" * 80)

    send_webhook(
        payload=captured_payload(),
        event_id="evt_E2E_001",
    )

    # ========================================================
    # TEST 3
    # INVALID SIGNATURE
    # ========================================================

    print("\n")
    print("-" * 80)
    print("TEST 3 — INVALID SIGNATURE")
    print("-" * 80)

    payload = captured_payload()

    raw_body = json.dumps(
        payload,
        separators=(",", ":"),
    )

    response = requests.post(

        WEBHOOK_URL,

        data=raw_body.encode("utf-8"),

        headers={

            "Content-Type":
                "application/json",

            "X-Razorpay-Signature":
                "INVALID_SIGNATURE",

            "x-razorpay-event-id":
                "evt_E2E_INVALID",

        },
    )

    print(
        "\nHTTP STATUS:",
        response.status_code,
    )

    print(
        json.dumps(
            response.json(),
            indent=2,
        )
    )


if __name__ == "__main__":

    main()