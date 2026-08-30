"""Phase 07.3 MongoDB persistence and transaction integrity test."""

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.database.mongodb import check_connection, get_database
from script.database.repositories.customer_repository import CustomerRepository
from script.database.repositories.order_repository import OrderRepository
from script.database.repositories.payment_repository import PaymentRepository
from script.database.repositories.product_repository import ProductRepository
from script.database.repositories.transaction_repository import TransactionRepository


REAL_CUSTOMER_ID = 5176
REAL_PRODUCT_ID = 453
TEST_CUSTOMER_ID = 999999001
TEST_PRODUCT_ID = 999999001


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    if not check_connection():
        print("MongoDB connection failed.")
        return 1

    db = get_database()
    run_id = "TEST-PERSISTENCE-" + uuid.uuid4().hex[:12]
    transaction_repo = TransactionRepository()

    try:
        assert_true(
            CustomerRepository().get_by_customer_id(REAL_CUSTOMER_ID),
            f"Customer {REAL_CUSTOMER_ID} not found.",
        )
        assert_true(
            ProductRepository().get_by_product_id(REAL_PRODUCT_ID),
            f"Product {REAL_PRODUCT_ID} not found.",
        )

        transaction = transaction_repo.create(
            customer_id=TEST_CUSTOMER_ID,
            product_id=TEST_PRODUCT_ID,
            original_price=1000.0,
            discount_percent=10.0,
            final_price=900.0,
            status="OFFER_REQUESTED",
            checkout_ready=False,
            payment_status="NOT_STARTED",
            payment_transaction_id=None,
            order_id=None,
            customer_accepted=False,
            test_run_id=run_id,
        )
        assert_true(transaction.get("transaction_id"), "Transaction ID was not generated.")
        assert_true(
            transaction_repo.get_by_customer_id(TEST_CUSTOMER_ID),
            "Created transaction could not be retrieved.",
        )
        assert_true(
            transaction_repo.update_status(TEST_CUSTOMER_ID, "COUNTER_OFFER"),
            "Transaction status update failed.",
        )
        assert_true(
            transaction_repo.update(
                TEST_CUSTOMER_ID,
                {"status": "OFFER_ACCEPTED", "customer_accepted": True},
            ),
            "Customer acceptance update failed.",
        )

        payment_id = "TXN-" + uuid.uuid4().hex[:12].upper()
        PaymentRepository().create(
            customer_id=TEST_CUSTOMER_ID,
            product_id=TEST_PRODUCT_ID,
            amount=900.0,
            currency="INR",
            payment_method="UPI",
            status="PAYMENT_SUCCESS",
            transaction_id=payment_id,
            reason="integration_test",
            test_run_id=run_id,
        )
        OrderRepository().create(
            customer_id=TEST_CUSTOMER_ID,
            product_id=TEST_PRODUCT_ID,
            amount=900.0,
            currency="INR",
            payment_status="SUCCESS",
            payment_transaction_id=payment_id,
            status="ORDER_CREATED",
            reason="integration_test",
            test_run_id=run_id,
        )

        failed_id = "TXN-FAILED-" + uuid.uuid4().hex[:10].upper()
        PaymentRepository().create(
            customer_id=TEST_CUSTOMER_ID,
            product_id=TEST_PRODUCT_ID,
            amount=900.0,
            currency="INR",
            payment_method="UPI",
            status="PAYMENT_FAILED",
            transaction_id=failed_id,
            reason="simulated_payment_failure",
            test_run_id=run_id,
        )
        assert_true(
            db.orders.count_documents({
                "test_run_id": run_id,
                "payment_transaction_id": failed_id,
            }) == 0,
            "Failed payment created an order.",
        )

        before = db.transactions.count_documents({"test_run_id": run_id})
        transaction_repo.create_or_update(
            customer_id=TEST_CUSTOMER_ID,
            product_id=TEST_PRODUCT_ID,
            status="OFFER_REQUESTED",
            test_run_id=run_id,
        )
        assert_true(
            db.transactions.count_documents({"test_run_id": run_id}) == before,
            "Duplicate transaction was created.",
        )

        print("ALL MONGODB PERSISTENCE TESTS PASSED")
        return 0
    finally:
        for collection in ("transactions", "payments", "orders"):
            db[collection].delete_many({"test_run_id": run_id})


if __name__ == "__main__":
    raise SystemExit(main())
