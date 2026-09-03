from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


@dataclass
class TransactionState:
    """
    Central transaction lifecycle owner.
    
    Tracks complete journey:
    1. Product selection + negotiation
    2. Checkout preparation
    3. Razorpay order creation + payment
    4. Payment verification + webhooks
    5. Internal order creation
    
    All payment providers and agents update
    this single source of truth.
    """

    OFFER_CREATED = "OFFER_CREATED"
    COUNTER_OFFERED = "COUNTER_OFFERED"
    CUSTOMER_ACCEPTED = "CUSTOMER_ACCEPTED"
    OFFER_ACCEPTED = CUSTOMER_ACCEPTED  # Backward-compatible alias
    CHECKOUT_READY = "CHECKOUT_READY"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_SUCCESS = PAYMENT_CAPTURED  # Backward-compatible alias
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CHECKOUT_FAILED = "CHECKOUT_FAILED"
    PAYMENT_VERIFICATION_FAILED = "PAYMENT_VERIFICATION_FAILED"
    ORDER_CREATED = "ORDER_CREATED"
    COMPLETED = "COMPLETED"
    ORDER_FAILED = "ORDER_FAILED"

    # ========================================================
    # CUSTOMER & PRODUCT
    # ========================================================

    customer_id: int

    product_id: Optional[int] = None

    quantity: int = 1

    # ========================================================
    # PRICING (ORIGINAL → NEGOTIATED → FINAL)
    # ========================================================

    original_price: float = 0.0

    price: float = 0.0

    negotiated_price: float = 0.0

    final_price: float = 0.0

    discount_percent: float = 0.0

    discount: float = 0.0

    negotiation_round: int = 0

    currency: str = "INR"

    # ========================================================
    # TRANSACTION LIFECYCLE
    # ========================================================

    transaction_id: str = ""

    status: str = "NO_TRANSACTION"

    created_at: str = ""

    updated_at: str = ""

    expires_at: str = ""

    is_active: bool = True

    customer_accepted: bool = False

    checkout_ready: bool = False

    # ========================================================
    # RAZORPAY INTEGRATION
    # ========================================================

    razorpay_order_id: Optional[str] = None

    razorpay_payment_id: Optional[str] = None

    payment_transaction_id: Optional[str] = None

    payment_status: str = "NOT_STARTED"

    # ========================================================
    # INTERNAL ORDER
    # ========================================================

    order_id: Optional[str] = None

    def __post_init__(self):
        if not self.transaction_id:
            self.transaction_id = "TRX-" + uuid4().hex[:12].upper()
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.expires_at:
            created_time = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            self.expires_at = (created_time.replace(microsecond=0) if created_time.tzinfo else created_time).isoformat()

        if self.price > 0 and self.original_price == 0:
            self.original_price = self.price
        if self.original_price > 0 and self.price == 0:
            self.price = self.original_price
        if self.discount > 0 and self.discount_percent == 0:
            self.discount_percent = self.discount
        if self.discount_percent > 0 and self.discount == 0:
            self.discount = self.discount_percent

        if self.negotiated_price == 0.0 and self.original_price > 0.0:
            self.negotiated_price = self.original_price

        if self.final_price == 0.0 and self.negotiated_price > 0.0:
            discount_amount = self.negotiated_price * (self.discount_percent / 100.0)
            self.final_price = self.negotiated_price - discount_amount

        if self.status in {"OFFER_CREATED", "COUNTER_OFFERED", "CHECKOUT_READY", "PAYMENT_PENDING", "PAYMENT_AUTHORIZED"}:
            self.is_active = True
        elif self.status in {"FAILED", "PAYMENT_FAILED", "CHECKOUT_FAILED", "ORDER_FAILED", "COMPLETED"}:
            self.is_active = False

        if self.expires_at and self.status in {"PAID", "PAYMENT_CAPTURED", "ORDER_CREATED", "COMPLETED", "FAILED"}:
            self.is_active = False