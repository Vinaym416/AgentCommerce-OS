from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Optional

from script.transaction.transaction_state import (
    TransactionState
)
from script.database.repositories.transaction_repository import (
    TransactionRepository
)


class TransactionManager:

    def __init__(self, repository=None):

        self.transactions: Dict[
            int,
            TransactionState
        ] = {}

        self.repository = repository or TransactionRepository()

    # ========================================================
    # GET STATE
    # ========================================================

    def get(
        self,
        customer_id: int
    ) -> Optional[TransactionState]:

        state = self.transactions.get(customer_id)

        if state is not None:
            return state

        document = self.repository.get_by_customer_id(customer_id)

        if document is None:
            return None

        document.pop("_id", None)
        state = TransactionState(**document)
        self.transactions[customer_id] = state
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

        for key, value in kwargs.items():

            if hasattr(state, key):
                setattr(
                    state,
                    key,
                    value
                )

            state.updated_at = datetime.now(timezone.utc).isoformat()
            self.repository.upsert(asdict(state))

        return state

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(
        self,
        customer_id: int
    ):

        self.transactions.pop(
            customer_id,
            None
        )