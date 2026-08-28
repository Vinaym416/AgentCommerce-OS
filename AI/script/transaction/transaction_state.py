from dataclasses import dataclass
from typing import Optional


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