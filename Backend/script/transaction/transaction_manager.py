from dataclasses import asdict, fields
from datetime import datetime, timezone
from typing import Dict, Optional

from script.transaction.transaction_state import (
    TransactionState
)

from script.database.repositories.transaction_repository import (
    TransactionRepository
)


class TransactionManager:
    """
    CENTRAL TRANSACTION LIFECYCLE OWNER
    
    This class manages the complete transaction journey:
    
    1. NEGOTIATION PHASE
       - original_price (catalog)
       - negotiated_price (after NegotiationAgent)
       - discount_percent (merchant decision)
       - final_price (= negotiated_price - discount)
       
    2. CHECKOUT PHASE
       - transaction persisted to MongoDB
       - razorpay_order_id created
       - payment_status = PENDING
       
    3. PAYMENT PHASE
       - razorpay_payment_id received from frontend
       - payment_transaction_id (Razorpay signature verification)
       - payment_status updated via webhook
       
    4. ORDER PHASE
       - order_id created after payment.captured webhook
       - status = ORDER_CREATED
    
    IMPORTANT: All payment providers and commerce agents
    update this single source of truth via TransactionManager.
    No other class owns the complete transaction state.
    """

    def __init__(
        self,
        repository=None
    ):

        self.transactions: Dict[
            int,
            TransactionState
        ] = {}

        self.repository = (
            repository
            or TransactionRepository()
        )


    # ========================================================
    # GET STATE
    # ========================================================

    def get(
        self,
        customer_id: int
    ) -> Optional[TransactionState]:

        state = self.transactions.get(
            customer_id
        )

        if state is not None:

            return state

        document = (
            self.repository
            .get_by_customer_id(
                customer_id
            )
        )

        if document is None:

            return None

        document.pop(
            "_id",
            None
        )

        allowed_fields = {f.name for f in fields(TransactionState)}
        document = {
            key: value
            for key, value in document.items()
            if key in allowed_fields
        }

        state = TransactionState(
            **document
        )

        self.transactions[
            customer_id
        ] = state

        return state

    # ========================================================
    # GET BY TRANSACTION ID
    # ========================================================

    def get_by_transaction_id(
        self,
        transaction_id: str
    ) -> Optional[TransactionState]:

        document = (
            self.repository
            .get_by_transaction_id(
                transaction_id
            )
        )

        if document is None:

            return None

        document.pop(
            "_id",
            None
        )

        allowed_fields = {f.name for f in fields(TransactionState)}
        document = {
            key: value
            for key, value in document.items()
            if key in allowed_fields
        }

        state = TransactionState(
            **document
        )

        self.transactions[
            state.customer_id
        ] = state

        return state

    # ========================================================
    # CREATE / UPDATE
    # ========================================================

    def create_or_update(
        self,
        customer_id: int,
        **kwargs
    ) -> TransactionState:

        state = self.transactions.get(
            customer_id
        )

        if state is None:
            state = TransactionState(
                customer_id=customer_id,
                product_id=kwargs.get("product_id"),
                price=kwargs.get("price", kwargs.get("original_price", 0.0)),
                discount=kwargs.get("discount", kwargs.get("discount_percent", 0.0)),
                status=kwargs.get("status", "OFFER_CREATED"),
            )
            self.transactions[customer_id] = state

        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        if "price" in kwargs or "original_price" in kwargs:
            price = kwargs.get("price", kwargs.get("original_price", state.original_price))
            state.price = float(price)
            state.original_price = float(price)

        if "discount" in kwargs or "discount_percent" in kwargs:
            discount = kwargs.get("discount", kwargs.get("discount_percent", state.discount_percent))
            state.discount = float(discount)
            state.discount_percent = float(discount)

        if state.status in {"OFFER_CREATED", "COUNTER_OFFERED", "CHECKOUT_READY", "PAYMENT_PENDING", "PAYMENT_AUTHORIZED"}:
            state.is_active = True
        elif state.status in {"FAILED", "PAYMENT_FAILED", "CHECKOUT_FAILED", "ORDER_FAILED", "COMPLETED"}:
            state.is_active = False

        if not state.created_at:
            state.created_at = datetime.now(timezone.utc).isoformat()
        if not state.expires_at:
            created_time = datetime.fromisoformat(state.created_at.replace("Z", "+00:00"))
            state.expires_at = (created_time + __import__("datetime").timedelta(minutes=5)).isoformat()

        state.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.upsert(asdict(state))
        return state

    def create_transaction(
        self,
        customer_id: int,
        product_id: int,
        price: float,
        discount: float,
        status: str = "OFFER_CREATED",
    ) -> Dict[str, object]:
        state = self.create_or_update(
            customer_id=customer_id,
            product_id=product_id,
            price=price,
            discount=discount,
            status=status,
        )
        return self.get_summary(state)

    def get_summary(self, state: TransactionState) -> Dict[str, object]:
        return {
            "transaction_id": state.transaction_id,
            "status": state.status,
            "created_at": state.created_at,
            "expires_at": state.expires_at,
            "is_active": bool(state.is_active),
        }

    # ========================================================
    # CLEAR MEMORY CACHE
    # ========================================================

    def clear(
        self,
        customer_id: int
    ):

        self.transactions.pop(
            customer_id,
            None
        )