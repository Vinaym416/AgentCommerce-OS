from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


@dataclass
class TransactionState:

    OFFER_CREATED = "OFFER_CREATED"
    COUNTER_OFFERED = "COUNTER_OFFERED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    CHECKOUT_READY = "CHECKOUT_READY"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_FAILED = "ORDER_FAILED"

    customer_id: int

    transaction_id: str = ""

    updated_at: str = ""

    product_id: Optional[int] = None

    original_price: float = 0.0

    discount_percent: float = 0.0

    final_price: float = 0.0

    status: str = "NO_TRANSACTION"

    checkout_ready: bool = False

    payment_status: str = "NOT_STARTED"

    payment_transaction_id: Optional[str] = None

    order_id: Optional[str] = None

    customer_accepted: bool = False

    def __post_init__(self):
        if not self.transaction_id:
            self.transaction_id = "TRX-" + uuid4().hex[:12].upper()
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()