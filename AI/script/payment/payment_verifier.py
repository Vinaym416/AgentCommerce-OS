"""
AGENTCOMMERCE OS
PHASE 08B — RAZORPAY PAYMENT VERIFIER

Responsible only for verifying the authenticity of a Razorpay
payment returned by the frontend.

Flow:

razorpay_order_id
        +
razorpay_payment_id
        ↓
HMAC-SHA256
        ↓
Compare with razorpay_signature
        ↓
VALID / INVALID

IMPORTANT:
This component does NOT:
- create Razorpay orders
- process payments
- create internal commerce orders
- handle webhooks

It only verifies the Razorpay payment signature.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# ============================================================
# VERIFICATION RESULT
# ============================================================

@dataclass
class PaymentVerificationResult:

    status: str

    valid: bool

    razorpay_order_id: Optional[str]

    razorpay_payment_id: Optional[str]

    reason: str


# ============================================================
# PAYMENT VERIFIER
# ============================================================

class PaymentVerifier:

    def __init__(
        self,
        key_secret: Optional[str] = None,
    ):

        self.key_secret = (
            key_secret
            if key_secret is not None
            else os.getenv("RAZORPAY_KEY_SECRET")
        )

        print(
            "Payment Verifier initialized."
        )

    # ========================================================
    # VERIFY PAYMENT SIGNATURE
    # ========================================================

    def verify_payment_signature(
        self,
        razorpay_order_id: Optional[str],
        razorpay_payment_id: Optional[str],
        razorpay_signature: Optional[str],
    ) -> PaymentVerificationResult:

        # ----------------------------------------------------
        # CREDENTIAL VALIDATION
        # ----------------------------------------------------

        if not self.key_secret:

            return PaymentVerificationResult(

                status="VERIFICATION_FAILED",

                valid=False,

                razorpay_order_id=razorpay_order_id,

                razorpay_payment_id=razorpay_payment_id,

                reason="razorpay_credentials_missing",
            )

        # ----------------------------------------------------
        # ORDER ID VALIDATION
        # ----------------------------------------------------

        if not razorpay_order_id:

            return PaymentVerificationResult(

                status="VERIFICATION_FAILED",

                valid=False,

                razorpay_order_id=None,

                razorpay_payment_id=razorpay_payment_id,

                reason="razorpay_order_id_required",
            )

        # ----------------------------------------------------
        # PAYMENT ID VALIDATION
        # ----------------------------------------------------

        if not razorpay_payment_id:

            return PaymentVerificationResult(

                status="VERIFICATION_FAILED",

                valid=False,

                razorpay_order_id=razorpay_order_id,

                razorpay_payment_id=None,

                reason="razorpay_payment_id_required",
            )

        # ----------------------------------------------------
        # SIGNATURE VALIDATION
        # ----------------------------------------------------

        if not razorpay_signature:

            return PaymentVerificationResult(

                status="VERIFICATION_FAILED",

                valid=False,

                razorpay_order_id=razorpay_order_id,

                razorpay_payment_id=razorpay_payment_id,

                reason="razorpay_signature_required",
            )

        # ----------------------------------------------------
        # CREATE SIGNATURE PAYLOAD
        # ----------------------------------------------------

        message = (
            f"{razorpay_order_id}|"
            f"{razorpay_payment_id}"
        )

        # ----------------------------------------------------
        # HMAC-SHA256
        # ----------------------------------------------------

        expected_signature = hmac.new(

            self.key_secret.encode("utf-8"),

            message.encode("utf-8"),

            hashlib.sha256

        ).hexdigest()

        # ----------------------------------------------------
        # CONSTANT-TIME COMPARISON
        # ----------------------------------------------------

        if not hmac.compare_digest(
            expected_signature,
            razorpay_signature,
        ):

            return PaymentVerificationResult(

                status="VERIFICATION_FAILED",

                valid=False,

                razorpay_order_id=razorpay_order_id,

                razorpay_payment_id=razorpay_payment_id,

                reason="invalid_payment_signature",
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return PaymentVerificationResult(

            status="PAYMENT_VERIFIED",

            valid=True,

            razorpay_order_id=razorpay_order_id,

            razorpay_payment_id=razorpay_payment_id,

            reason="payment_signature_verified",
        )


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — PAYMENT VERIFIER"
    )

    print("=" * 80)

    # Test-only secret.
    # NEVER hard-code a real production secret.

    verifier = PaymentVerifier(
        key_secret="TEST_SECRET_123"
    )

    order_id = "order_TEST123"

    payment_id = "pay_TEST456"

    # --------------------------------------------------------
    # Generate test signature
    # --------------------------------------------------------

    message = (
        f"{order_id}|{payment_id}"
    )

    signature = hmac.new(

        b"TEST_SECRET_123",

        message.encode("utf-8"),

        hashlib.sha256

    ).hexdigest()

    print("\n")
    print("-" * 80)
    print("TEST — VALID SIGNATURE")
    print("-" * 80)

    print(
        verifier.verify_payment_signature(

            razorpay_order_id=order_id,

            razorpay_payment_id=payment_id,

            razorpay_signature=signature,
        )
    )

    print("\n")
    print("-" * 80)
    print("TEST — INVALID SIGNATURE")
    print("-" * 80)

    print(
        verifier.verify_payment_signature(

            razorpay_order_id=order_id,

            razorpay_payment_id=payment_id,

            razorpay_signature="INVALID_SIGNATURE",
        )
    )


if __name__ == "__main__":

    main()