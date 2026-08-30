"""
AGENTCOMMERCE OS
MongoDB Index Configuration
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.database.mongodb import get_database


def create_indexes():

    db = get_database()


    # ========================================================
    # CUSTOMERS
    # ========================================================

    db.customers.create_index(
        "customer_id",
        unique=True
    )


    # ========================================================
    # PRODUCTS
    # ========================================================

    db.products.create_index(
        "product_id",
        unique=True
    )


    # ========================================================
    # TRANSACTIONS
    # ========================================================

    db.transactions.create_index(
        "transaction_id",
        unique=True
    )

    db.transactions.create_index(
        "customer_id"
    )

    db.transactions.create_index(
        [
            ("customer_id", 1),
            ("updated_at", -1),
        ]
    )


    # ========================================================
    # PAYMENTS
    # ========================================================

    db.payments.create_index(
        "transaction_id",
        unique=True
    )

    db.payments.create_index(
        "customer_id"
    )


    # ========================================================
    # ORDERS
    # ========================================================

    db.orders.create_index(
        "order_id",
        unique=True
    )

    db.orders.create_index(
        "customer_id"
    )


    # ========================================================
    # MERCHANT DECISIONS
    # ========================================================

    db.merchant_decisions.create_index(
        "product_id"
    )

    db.merchant_decisions.create_index(
        "created_at"
    )


    # ========================================================
    # EVENTS
    # ========================================================

    db.commerce_events.create_index(
        "customer_id"
    )

    db.commerce_events.create_index(
        "created_at"
    )


    print(
        "MongoDB indexes created successfully."
    )


if __name__ == "__main__":

    create_indexes()