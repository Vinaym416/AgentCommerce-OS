"""Legacy test/mock payment agent.

This class intentionally represents the old simulated payment flow and is not part
of the production payment architecture. Real payment handling is delegated to the
Razorpay-backed services and webhooks.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4


@dataclass
class PaymentResult:
    status: str
    product_id: Optional[int]
    amount: float
    currency: str
    payment_method: str
    transaction_id: Optional[str]
    reason: str


class PaymentAgent:
    """Legacy simulated payment boundary kept only for tests and mocks."""

    SUPPORTED_PAYMENT_METHODS = {
        "UPI",
        "CARD",
        "NET_BANKING",
        "WALLET",
    }

    def __init__(self):
        warnings.warn(
            "PaymentAgent is legacy and should only be used in tests/mocks; "
            "use the Razorpay-based payment flow in production.",
            DeprecationWarning,
            stacklevel=2,
        )
        print("Legacy Payment Agent initialized for test/mock use only.")

    def process_payment(
        self,
        product_id: int,
        amount: float,
        payment_method: str = "UPI",
        simulate_failure: bool = False,
    ) -> PaymentResult:
        if amount <= 0:
            return PaymentResult(
                status="PAYMENT_FAILED",
                product_id=product_id,
                amount=round(amount, 2),
                currency="INR",
                payment_method=payment_method,
                transaction_id=None,
                reason="invalid_amount",
            )

        normalized_method = payment_method.upper()
        if normalized_method not in self.SUPPORTED_PAYMENT_METHODS:
            return PaymentResult(
                status="PAYMENT_FAILED",
                product_id=product_id,
                amount=round(amount, 2),
                currency="INR",
                payment_method=payment_method,
                transaction_id=None,
                reason="unsupported_payment_method",
            )

        if simulate_failure:
            return PaymentResult(
                status="PAYMENT_FAILED",
                product_id=product_id,
                amount=round(amount, 2),
                currency="INR",
                payment_method=normalized_method,
                transaction_id=None,
                reason="payment_declined",
            )

        return PaymentResult(
            status="PAYMENT_SUCCESS",
            product_id=product_id,
            amount=round(amount, 2),
            currency="INR",
            payment_method=normalized_method,
            transaction_id=f"TXN-{uuid4().hex[:12].upper()}",
            reason="payment_processed_successfully",
        )
