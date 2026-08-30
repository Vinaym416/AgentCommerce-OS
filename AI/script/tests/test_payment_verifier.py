"""
AGENTCOMMERCE OS
PHASE 08B — PAYMENT VERIFIER TEST SUITE
"""

import hashlib
import hmac
import os
import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from script.payment.payment_verifier import (
    PaymentVerifier,
    PaymentVerificationResult,
)


# ============================================================
# HELPERS
# ============================================================

TEST_SECRET = "TEST_SECRET_123"

ORDER_ID = "order_TEST123"

PAYMENT_ID = "pay_TEST456"


def generate_signature(
    secret=TEST_SECRET,
    order_id=ORDER_ID,
    payment_id=PAYMENT_ID,
):

    message = (
        f"{order_id}|{payment_id}"
    )

    return hmac.new(

        secret.encode("utf-8"),

        message.encode("utf-8"),

        hashlib.sha256

    ).hexdigest()


# ============================================================
# TEST RUNNER
# ============================================================

total_tests = 0
passed_tests = 0


def check(
    condition,
    description,
):

    global total_tests
    global passed_tests

    total_tests += 1

    if condition:

        passed_tests += 1

        print(
            f"[PASS] {description}"
        )

    else:

        print(
            f"[FAIL] {description}"
        )


# ============================================================
# TEST 1 — RESULT TYPE
# ============================================================

print("=" * 80)

print(
    "AGENTCOMMERCE OS"
)

print(
    "PHASE 08B — PAYMENT VERIFIER TEST SUITE"
)

print("=" * 80)


verifier = PaymentVerifier(
    key_secret=TEST_SECRET
)

valid_signature = generate_signature()

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature=valid_signature,
)


check(
    isinstance(
        result,
        PaymentVerificationResult
    ),
    "Verification returns PaymentVerificationResult",
)

check(
    result.valid is True,
    "Valid signature accepted",
)

check(
    result.status == "PAYMENT_VERIFIED",
    "Correct success status",
)

check(
    result.razorpay_order_id == ORDER_ID,
    "Order ID preserved",
)

check(
    result.razorpay_payment_id == PAYMENT_ID,
    "Payment ID preserved",
)

check(
    result.reason
    == "payment_signature_verified",
    "Correct success reason",
)


# ============================================================
# TEST 2 — INVALID SIGNATURE
# ============================================================

verifier = PaymentVerifier(
    key_secret=TEST_SECRET
)

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature="INVALID_SIGNATURE",
)


check(
    result.valid is False,
    "Invalid signature rejected",
)

check(
    result.status
    == "VERIFICATION_FAILED",
    "Invalid signature returns failure status",
)

check(
    result.reason
    == "invalid_payment_signature",
    "Correct invalid signature reason",
)


# ============================================================
# TEST 3 — TAMPERED ORDER ID
# ============================================================

result = verifier.verify_payment_signature(

    razorpay_order_id="order_TAMPERED",

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature=valid_signature,
)


check(
    result.valid is False,
    "Tampered order ID rejected",
)

check(
    result.reason
    == "invalid_payment_signature",
    "Tampered order ID returns invalid signature",
)


# ============================================================
# TEST 4 — TAMPERED PAYMENT ID
# ============================================================

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id="pay_TAMPERED",

    razorpay_signature=valid_signature,
)


check(
    result.valid is False,
    "Tampered payment ID rejected",
)

check(
    result.reason
    == "invalid_payment_signature",
    "Tampered payment ID returns invalid signature",
)


# ============================================================
# TEST 5 — MISSING SECRET
# ============================================================

verifier = PaymentVerifier(
    key_secret=None
)

# Prevent environment credentials from affecting this test.

original_secret = os.environ.pop(
    "RAZORPAY_KEY_SECRET",
    None,
)

try:

    result = verifier.verify_payment_signature(

        razorpay_order_id=ORDER_ID,

        razorpay_payment_id=PAYMENT_ID,

        razorpay_signature=valid_signature,
    )

    check(
        result.valid is False,
        "Missing credentials rejected",
    )

    check(
        result.reason
        == "razorpay_credentials_missing",
        "Correct missing credential reason",
    )

finally:

    if original_secret is not None:

        os.environ[
            "RAZORPAY_KEY_SECRET"
        ] = original_secret


# ============================================================
# TEST 6 — MISSING ORDER ID
# ============================================================

verifier = PaymentVerifier(
    key_secret=TEST_SECRET
)

result = verifier.verify_payment_signature(

    razorpay_order_id=None,

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature=valid_signature,
)


check(
    result.valid is False,
    "Missing order ID rejected",
)

check(
    result.reason
    == "razorpay_order_id_required",
    "Correct missing order ID reason",
)


# ============================================================
# TEST 7 — MISSING PAYMENT ID
# ============================================================

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id=None,

    razorpay_signature=valid_signature,
)


check(
    result.valid is False,
    "Missing payment ID rejected",
)

check(
    result.reason
    == "razorpay_payment_id_required",
    "Correct missing payment ID reason",
)


# ============================================================
# TEST 8 — MISSING SIGNATURE
# ============================================================

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature=None,
)


check(
    result.valid is False,
    "Missing signature rejected",
)

check(
    result.reason
    == "razorpay_signature_required",
    "Correct missing signature reason",
)


# ============================================================
# TEST 9 — DIFFERENT SECRET
# ============================================================

wrong_signature = generate_signature(
    secret="WRONG_SECRET"
)

result = verifier.verify_payment_signature(

    razorpay_order_id=ORDER_ID,

    razorpay_payment_id=PAYMENT_ID,

    razorpay_signature=wrong_signature,
)


check(
    result.valid is False,
    "Signature generated with wrong secret rejected",
)

check(
    result.reason
    == "invalid_payment_signature",
    "Wrong secret returns invalid signature",
)


# ============================================================
# TEST 10 — UNIQUE SIGNATURE INPUT
# ============================================================

signature_a = generate_signature(
    payment_id="pay_A"
)

signature_b = generate_signature(
    payment_id="pay_B"
)

check(
    signature_a != signature_b,
    "Different payment IDs produce different signatures",
)


# ============================================================
# SUMMARY
# ============================================================

print()

print("=" * 80)

print(
    "PHASE 08B PAYMENT VERIFIER TEST SUMMARY"
)

print("=" * 80)

print(
    f"Total tests : {total_tests}"
)

print(
    f"Passed      : {passed_tests}"
)

print(
    f"Failed      : {total_tests - passed_tests}"
)

print("=" * 80)

if passed_tests == total_tests:

    print(
        "ALL PHASE 08B PAYMENT VERIFIER TESTS PASSED"
    )

else:

    print(
        "PHASE 08B PAYMENT VERIFIER TESTS FAILED"
    )

    raise SystemExit(1)