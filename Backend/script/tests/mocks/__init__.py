"""Legacy/mock-only infrastructure for tests.

Production payment processing is handled by the Razorpay-backed flow.
"""

from .payment_agent import PaymentAgent, PaymentResult

__all__ = ["PaymentAgent", "PaymentResult"]
