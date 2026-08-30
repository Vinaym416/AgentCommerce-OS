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
                customer_id=customer_id
            )

            self.transactions[
                customer_id
            ] = state

        # ----------------------------------------------------
        # APPLY ALL CHANGES
        # ----------------------------------------------------

        for key, value in kwargs.items():

            if hasattr(state, key):

                setattr(
                    state,
                    key,
                    value
                )

        # ----------------------------------------------------
        # UPDATE TIMESTAMP ONCE
        # ----------------------------------------------------

        state.updated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        # ----------------------------------------------------
        # PERSIST ONCE
        # ----------------------------------------------------

        self.repository.upsert(
            asdict(state)
        )

        return state

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