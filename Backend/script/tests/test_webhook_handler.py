"""
AGENTCOMMERCE OS
PHASE 08C — RAZORPAY WEBHOOK HANDLER TEST SUITE
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.payment.webhook_handler import (
    RazorpayWebhookHandler,
    generate_test_signature,
)


# ============================================================
# HELPERS
# ============================================================

SECRET = "TEST_WEBHOOK_SECRET"


def create_handler():

    return RazorpayWebhookHandler(
        webhook_secret=SECRET
    )


def payment_captured_payload():

    return {

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


def payment_failed_payload():

    return {

        "entity": "event",

        "event": "payment.failed",

        "payload": {

            "payment": {

                "entity": {

                    "id": "pay_FAILED123",

                    "order_id": "order_TEST123",

                    "status": "failed"

                }

            }

        }

    }


def order_paid_payload():

    return {

        "entity": "event",

        "event": "order.paid",

        "payload": {

            "order": {

                "entity": {

                    "id": "order_TEST123",

                    "status": "paid"

                }

            }

        }

    }


def raw_payload(payload):

    return json.dumps(
        payload,
        separators=(",", ":")
    )


def sign(body):

    return generate_test_signature(
        body,
        SECRET
    )


# ============================================================
# TEST RUNNER
# ============================================================

total = 0
passed = 0


def check(
    condition,
    message,
):

    global total
    global passed

    total += 1

    if condition:

        passed += 1

        print(
            f"[PASS] {message}"
        )

    else:

        print(
            f"[FAIL] {message}"
        )


# ============================================================
# TEST 1 — VALID PAYMENT CAPTURED
# ============================================================

print("\n")
print("-" * 80)
print("TEST 1 — VALID PAYMENT CAPTURED")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    payment_captured_payload()
)

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_001"

)

check(
    result.valid,
    "Valid webhook accepted"
)

check(
    result.status == "WEBHOOK_ACCEPTED",
    "Correct accepted status"
)

check(
    result.event == "payment.captured",
    "Correct event detected"
)

check(
    result.razorpay_payment_id
    == "pay_TEST456",
    "Payment ID extracted"
)

check(
    result.razorpay_order_id
    == "order_TEST123",
    "Order ID extracted"
)

check(
    result.payment_status
    == "captured",
    "Payment status extracted"
)


# ============================================================
# TEST 2 — INVALID SIGNATURE
# ============================================================

print("\n")
print("-" * 80)
print("TEST 2 — INVALID SIGNATURE")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    payment_captured_payload()
)

result = handler.handle(

    raw_body=body,

    signature="INVALID_SIGNATURE",

    event_id="evt_002"

)

check(
    not result.valid,
    "Invalid signature rejected"
)

check(
    result.status
    == "WEBHOOK_REJECTED",
    "Correct rejection status"
)

check(
    result.reason
    == "invalid_webhook_signature",
    "Correct invalid signature reason"
)


# ============================================================
# TEST 3 — MISSING SECRET
# ============================================================

print("\n")
print("-" * 80)
print("TEST 3 — MISSING SECRET")
print("-" * 80)

handler = RazorpayWebhookHandler()

body = raw_payload(
    payment_captured_payload()
)

result = handler.handle(

    raw_body=body,

    signature="anything",

    event_id="evt_003"

)

check(
    not result.valid,
    "Missing secret rejected"
)

check(
    result.reason
    == "webhook_secret_missing",
    "Correct missing secret reason"
)


# ============================================================
# TEST 4 — MISSING SIGNATURE
# ============================================================

print("\n")
print("-" * 80)
print("TEST 4 — MISSING SIGNATURE")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    payment_captured_payload()
)

result = handler.handle(

    raw_body=body,

    signature=None,

    event_id="evt_004"

)

check(
    not result.valid,
    "Missing signature rejected"
)

check(
    result.reason
    == "webhook_signature_missing",
    "Correct missing signature reason"
)


# ============================================================
# TEST 5 — INVALID JSON
# ============================================================

print("\n")
print("-" * 80)
print("TEST 5 — INVALID JSON")
print("-" * 80)

handler = create_handler()

body = "{invalid-json"

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_005"

)

check(
    not result.valid,
    "Invalid JSON rejected"
)

check(
    result.reason
    == "invalid_webhook_payload",
    "Correct invalid payload reason"
)


# ============================================================
# TEST 6 — MISSING EVENT
# ============================================================

print("\n")
print("-" * 80)
print("TEST 6 — MISSING EVENT")
print("-" * 80)

handler = create_handler()

payload = {
    "entity": "event",
    "payload": {}
}

body = raw_payload(payload)

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_006"

)

check(
    not result.valid,
    "Missing event rejected"
)

check(
    result.reason
    == "webhook_event_missing",
    "Correct missing event reason"
)


# ============================================================
# TEST 7 — UNSUPPORTED EVENT
# ============================================================

print("\n")
print("-" * 80)
print("TEST 7 — UNSUPPORTED EVENT")
print("-" * 80)

handler = create_handler()

payload = {

    "entity": "event",

    "event": "refund.created",

    "payload": {}

}

body = raw_payload(payload)

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_007"

)

check(
    result.valid,
    "Unsupported event signature still verified"
)

check(
    result.status
    == "WEBHOOK_IGNORED",
    "Unsupported event ignored safely"
)

check(
    result.reason
    == "unsupported_webhook_event",
    "Correct unsupported event reason"
)


# ============================================================
# TEST 8 — PAYMENT FAILED
# ============================================================

print("\n")
print("-" * 80)
print("TEST 8 — PAYMENT FAILED")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    payment_failed_payload()
)

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_008"

)

check(
    result.valid,
    "Payment failed webhook accepted"
)

check(
    result.event
    == "payment.failed",
    "Payment failed event detected"
)

check(
    result.payment_status
    == "failed",
    "Failed payment status extracted"
)

check(
    result.razorpay_payment_id
    == "pay_FAILED123",
    "Failed payment ID extracted"
)


# ============================================================
# TEST 9 — ORDER PAID
# ============================================================

print("\n")
print("-" * 80)
print("TEST 9 — ORDER PAID")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    order_paid_payload()
)

result = handler.handle(

    raw_body=body,

    signature=sign(body),

    event_id="evt_009"

)

check(
    result.valid,
    "Order paid webhook accepted"
)

check(
    result.event
    == "order.paid",
    "Order paid event detected"
)

check(
    result.razorpay_order_id
    == "order_TEST123",
    "Order ID extracted"
)

check(
    result.payment_status
    == "paid",
    "Order paid status extracted"
)


# ============================================================
# TEST 10 — DUPLICATE EVENT
# ============================================================

print("\n")
print("-" * 80)
print("TEST 10 — DUPLICATE EVENT")
print("-" * 80)

handler = create_handler()

body = raw_payload(
    payment_captured_payload()
)

signature = sign(body)

first = handler.handle(

    raw_body=body,

    signature=signature,

    event_id="evt_DUPLICATE"

)

second = handler.handle(

    raw_body=body,

    signature=signature,

    event_id="evt_DUPLICATE"

)

check(
    first.status
    == "WEBHOOK_ACCEPTED",
    "First webhook accepted"
)

check(
    second.status
    == "WEBHOOK_DUPLICATE",
    "Duplicate webhook detected"
)

check(
    second.reason
    == "duplicate_webhook_event",
    "Correct duplicate event reason"
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print(
    "PHASE 08C WEBHOOK HANDLER TEST SUMMARY"
)
print("=" * 80)

print(
    f"Total tests : {total}"
)

print(
    f"Passed      : {passed}"
)

print(
    f"Failed      : {total - passed}"
)

print("=" * 80)

if passed == total:

    print(
        "ALL PHASE 08C WEBHOOK HANDLER TESTS PASSED"
    )

else:

    print(
        "SOME PHASE 08C WEBHOOK HANDLER TESTS FAILED"
    )