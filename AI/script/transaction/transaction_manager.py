from typing import Dict, Optional

from script.transaction.transaction_state import (
    TransactionState
)


class TransactionManager:

    def __init__(self):

        self.transactions: Dict[
            int,
            TransactionState
        ] = {}

    # ========================================================
    # GET STATE
    # ========================================================

    def get(
        self,
        customer_id: int
    ) -> Optional[TransactionState]:

        return self.transactions.get(
            customer_id
        )

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