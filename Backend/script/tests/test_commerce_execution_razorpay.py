
"""
AGENTCOMMERCE OS
PHASE 08D — COMMERCE EXECUTION RAZORPAY TEST SUITE

Tests:

Checkout
    ↓
Razorpay Order
    ↓
Payment Verification
    ↓
Internal Order

IMPORTANT:

These tests do NOT call the real Razorpay API.

RazorpayClient is replaced with a fake client.

Therefore:

- No real payment
- No real money
- No API credentials required
- No external network dependency
"""

import sys
from pathlib import Path
from unittest.mock import patch


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORTS
# ============================================================

from script.agents.commerce_execution_agent import (
    CommerceExecutionAgent
)

from script.payment.razorpay_client import (
    RazorpayOrderResult
)

from script.payment.payment_verifier import (
    PaymentVerificationResult,
    PaymentVerifier,
)
from script.payment.webhook_handler import RazorpayWebhookHandler
from script.webhook.webhook_service import WebhookService
from script.database.repositories.transaction_repository import TransactionRepository
from script.database.repositories.order_repository import OrderRepository


# ============================================================
# TEST COUNTERS
# ============================================================

total_tests = 0
passed_tests = 0


def check(condition, message):

    global total_tests
    global passed_tests

    total_tests += 1

    if condition:

        passed_tests += 1

        print(
            f"[PASS] {message}"
        )

    else:

        print(
            f"[FAIL] {message}"
        )


# ============================================================
# FAKE RAZORPAY CLIENT
# ============================================================

class FakeRazorpayClient:

    def __init__(self):

        self.created_orders = []

    def create_order(
        self,
        *,
        amount,
        currency="INR",
        receipt=None,
        notes=None,
    ):

        self.created_orders.append({
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
        })

        return RazorpayOrderResult(
            status="RAZORPAY_ORDER_CREATED",
            success=True,
            razorpay_order_id="order_TEST123",
            amount=amount,
            amount_in_paise=int(
                round(amount * 100)
            ),
            currency=currency,
            receipt=receipt,
            razorpay_status="created",
            reason="razorpay_order_created",
            raw_response={
                "id": "order_TEST123",
                "amount": int(
                    round(amount * 100)
                ),
                "currency": currency,
                "status": "created",
            },
        )


# ============================================================
# FAKE PAYMENT VERIFIER
# ============================================================

class FakePaymentVerifier:

    def __init__(
        self,
        valid=True,
    ):

        self.valid = valid

    def verify_payment_signature(
        self,
        *,
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
    ):

        if self.valid:

            return PaymentVerificationResult(
                status="PAYMENT_VERIFIED",
                valid=True,
                razorpay_order_id=(
                    razorpay_order_id
                ),
                razorpay_payment_id=(
                    razorpay_payment_id
                ),
                reason="payment_signature_verified",
            )

        return PaymentVerificationResult(
            status="VERIFICATION_FAILED",
            valid=False,
            razorpay_order_id=(
                razorpay_order_id
            ),
            razorpay_payment_id=(
                razorpay_payment_id
            ),
            reason="invalid_payment_signature",
        )


# ============================================================
# TEST 1 — CHECKOUT ONLY
# ============================================================

def test_checkout_only():

    print()
    print("-" * 80)
    print("TEST 1 — CHECKOUT ONLY")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(),
    )

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=False,
    )

    check(
        isinstance(result, dict),
        "Execution returns dictionary"
    )

    check(
        result["checkout"] is not None,
        "Checkout result exists"
    )

    check(
        result["checkout"]["status"]
        == "CHECKOUT_READY",
        "Checkout is ready"
    )

    check(
        result["checkout"]["final_price"]
        == 705.81,
        "Discounted checkout price correct"
    )

    check(
        result["razorpay_order"] is None,
        "Razorpay order not created"
    )

    check(
        result["order"] is None,
        "Internal order not created"
    )

    check(
        result["final_action"]
        == "CHECKOUT_READY",
        "Execution stops at checkout"
    )


# ============================================================
# TEST 2 — RAZORPAY ORDER CREATION
# ============================================================

def test_razorpay_order_creation():

    print()
    print("-" * 80)
    print("TEST 2 — RAZORPAY ORDER CREATION")
    print("-" * 80)

    fake_client = FakeRazorpayClient()

    agent = CommerceExecutionAgent(
        razorpay_client=fake_client,
        payment_verifier=FakePaymentVerifier(),
    )

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=True,
    )

    check(
        result["checkout"] is not None,
        "Checkout exists"
    )

    check(
        result["razorpay_order"] is not None,
        "Razorpay order exists"
    )

    check(
        result["razorpay_order"]["success"] is True,
        "Razorpay order creation succeeds"
    )

    check(
        result["razorpay_order"]["razorpay_order_id"]
        == "order_TEST123",
        "Razorpay order ID preserved"
    )

    check(
        result["razorpay_order"]["amount"]
        == 705.81,
        "Razorpay order amount matches checkout"
    )

    check(
        result["razorpay_order"]["amount_in_paise"]
        == 70581,
        "Amount converted to paise"
    )

    check(
        result["order"] is None,
        "Internal order not created yet"
    )

    check(
        result["final_action"]
        == "PAYMENT_PENDING",
        "Payment remains pending"
    )

    check(
        len(fake_client.created_orders) == 1,
        "Exactly one Razorpay order created"
    )


# ============================================================
# TEST 3 — PAYMENT VERIFICATION SUCCESS
# ============================================================

def test_payment_verification_success():

    print()
    print("-" * 80)
    print("TEST 3 — PAYMENT VERIFICATION SUCCESS")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(
            valid=True
        ),
    )

    result = agent.verify_payment(
        customer_id=5176,
        product_id=453,
        product_price=99999.99,
        discount_percent=99,
        razorpay_order_id="order_TEST123",
        razorpay_payment_id="pay_TEST456",
        razorpay_signature="valid-signature",
    )

    check(
        "CLIENT_PRICE_FIELDS_IGNORED" in result["agent_trace"],
        "Client price fields are explicitly ignored during verification"
    )

    check(
        result["payment_verification"] is not None,
        "Payment verification result exists"
    )

    check(
        result["payment_verification"]["valid"]
        is True,
        "Payment signature verified"
    )

    check(
        result["payment_verification"]
        ["razorpay_order_id"]
        == "order_TEST123",
        "Razorpay order ID preserved"
    )

    check(
        result["payment_verification"]
        ["razorpay_payment_id"]
        == "pay_TEST456",
        "Razorpay payment ID preserved"
    )

    check(
        result["order"] is not None,
        "Internal order created"
    )

    check(
        result["order"]["status"]
        == "ORDER_CREATED",
        "Internal order successfully created"
    )

    check(
        result["order"]["amount"]
        == 705.81,
        "Internal order uses checkout amount"
    )

    check(
        result["order"]["payment_transaction_id"]
        == "pay_TEST456",
        "Internal order linked to Razorpay payment"
    )

    check(
        result["final_action"]
        == "ORDER_CREATED",
        "Final action is ORDER_CREATED"
    )


# ============================================================
# TEST 4 — INVALID PAYMENT SIGNATURE
# ============================================================

def test_invalid_payment_signature():

    print()
    print("-" * 80)
    print("TEST 4 — INVALID PAYMENT SIGNATURE")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(
            valid=False
        ),
    )

    result = agent.verify_payment(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        razorpay_order_id="order_TEST123",
        razorpay_payment_id="pay_TEST456",
        razorpay_signature="invalid-signature",
    )

    check(
        result["payment_verification"] is not None,
        "Verification result exists"
    )

    check(
        result["payment_verification"]["valid"]
        is False,
        "Invalid signature rejected"
    )

    check(
        result["payment_verification"]["reason"]
        == "invalid_payment_signature",
        "Correct invalid signature reason"
    )

    check(
        result["order"] is None,
        "Internal order NOT created"
    )

    check(
        result["final_action"]
        == "PAYMENT_VERIFICATION_FAILED",
        "Final action is verification failure"
    )


# ============================================================
# TEST 4B — DUPLICATE VERIFY IS IDEMPOTENT
# ============================================================

def test_duplicate_verify_is_idempotent():

    print()
    print("-" * 80)
    print("TEST 4B — DUPLICATE VERIFY IS IDEMPOTENT")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(valid=True),
    )

    order_id = "order_DUPLICATE_VERIFY"
    payment_id = "pay_DUPLICATE_VERIFY"
    customer_id = 7777
    product_id = 999
    amount = 250.0

    tx_repo = TransactionRepository()
    tx_repo.upsert({
        "transaction_id": "TRX-DUPLICATE-VERIFY",
        "customer_id": customer_id,
        "product_id": product_id,
        "original_price": amount,
        "negotiated_price": amount,
        "final_price": amount,
        "discount_percent": 0,
        "currency": "INR",
        "status": "PAYMENT_PENDING",
        "payment_status": "PENDING",
        "razorpay_order_id": order_id,
        "checkout_ready": True,
    })

    first = agent.verify_payment(
        customer_id=customer_id,
        transaction_id="TRX-DUPLICATE-VERIFY",
        product_id=product_id,
        product_price=999999,
        discount_percent=99,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature="valid-signature",
    )

    second = agent.verify_payment(
        customer_id=customer_id,
        transaction_id="TRX-DUPLICATE-VERIFY",
        product_id=product_id,
        product_price=999999,
        discount_percent=99,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature="valid-signature",
    )

    order_repo = OrderRepository()
    stored_orders = list(order_repo.collection.find({
        "payment_transaction_id": payment_id
    }, {"_id": 0}))

    check(
        first["final_action"] == "ORDER_CREATED",
        "First verification creates the order"
    )

    check(
        len(stored_orders) == 1,
        "Only one internal order exists for the same payment"
    )

    check(
        second["final_action"] == "ORDER_CREATED",
        "Second verification stays idempotent"
    )


# ============================================================
# TEST 4C — WEBHOOK BEFORE FRONTEND VERIFICATION
# ============================================================

def test_webhook_before_frontend_verification_is_idempotent():

    print()
    print("-" * 80)
    print("TEST 4C — WEBHOOK BEFORE FRONTEND VERIFICATION")
    print("-" * 80)

    webhook_service = WebhookService()
    tx_repo = TransactionRepository()
    order_repo = OrderRepository()

    transaction_id = "TRX-WEBHOOK-BEFORE-FRONTEND"
    order_id = "order_WEBHOOK_BEFORE_VERIFY"
    payment_id = "pay_WEBHOOK_BEFORE_VERIFY"
    customer_id = 8888
    product_id = 555
    amount = 300.0

    tx_repo.upsert({
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "product_id": product_id,
        "original_price": amount,
        "negotiated_price": amount,
        "final_price": amount,
        "discount_percent": 0,
        "currency": "INR",
        "status": "PAYMENT_PENDING",
        "payment_status": "PENDING",
        "razorpay_order_id": order_id,
        "checkout_ready": True,
    })

    first = webhook_service._create_order_for_payment(
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        event_id="evt_webhook_before_verify_1",
    )

    second = webhook_service._create_order_for_payment(
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        event_id="evt_webhook_before_verify_2",
    )

    stored_orders = list(order_repo.collection.find({
        "payment_transaction_id": payment_id
    }, {"_id": 0}))

    check(
        first["success"] is True,
        "Webhook-created order succeeds on first pass"
    )

    check(
        second["duplicate"] is True,
        "Duplicate webhook order is suppressed"
    )

    check(
        len(stored_orders) == 1,
        "Only one internal order exists when webhook precedes frontend verification"
    )


# ============================================================
# TEST 5 — PRICE CONSISTENCY
# ============================================================

def test_price_consistency():

    print()
    print("-" * 80)
    print("TEST 5 — PRICE CONSISTENCY")
    print("-" * 80)

    fake_client = FakeRazorpayClient()

    agent = CommerceExecutionAgent(
        razorpay_client=fake_client,
        payment_verifier=FakePaymentVerifier(
            valid=True
        ),
    )

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=1000,
        discount_percent=20,
        execute_payment=True,
    )

    check(
        result["checkout"]["final_price"]
        == 800,
        "Checkout final price is 800"
    )

    check(
        result["razorpay_order"]["amount"]
        == 800,
        "Razorpay order uses approved price"
    )

    check(
        result["razorpay_order"]["amount_in_paise"]
        == 80000,
        "Razorpay amount is 80000 paise"
    )


# ============================================================
# TEST 6 — TRACE
# ============================================================

def test_execution_trace():

    print()
    print("-" * 80)
    print("TEST 6 — RAZORPAY EXECUTION TRACE")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(
            valid=True
        ),
    )

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=True,
    )

    trace = result["agent_trace"]

    check(
        "CHECKOUT" in trace,
        "Trace contains CHECKOUT"
    )

    check(
        "CHECKOUT_READY" in trace,
        "Trace contains CHECKOUT_READY"
    )

    check(
        "RAZORPAY_ORDER" in trace,
        "Trace contains RAZORPAY_ORDER"
    )

    check(
        "RAZORPAY_ORDER_CREATED" in trace,
        "Trace contains RAZORPAY_ORDER_CREATED"
    )

    check(
        "PAYMENT_PENDING" in trace,
        "Trace contains PAYMENT_PENDING"
    )


# ============================================================
# TEST 7 — INVALID PRICE
# ============================================================

def test_invalid_price():

    print()
    print("-" * 80)
    print("TEST 7 — INVALID PRICE")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(),
    )

    result = agent.execute(
        customer_id=5176,
        product_id=453,
        product_price=0,
        discount_percent=10,
        execute_payment=True,
    )

    check(
        result["checkout"] is None,
        "Invalid price prevents checkout"
    )

    check(
        result["razorpay_order"] is None,
        "Invalid price prevents Razorpay order"
    )

    check(
        result["order"] is None,
        "Invalid price prevents internal order"
    )

    check(
        result["final_action"]
        == "EXECUTION_FAILED",
        "Invalid price returns EXECUTION_FAILED"
    )

    check(
        result["reason"]
        == "product_price_must_be_positive",
        "Correct invalid price reason"
    )


# ============================================================
# TEST 8 — ANONYMOUS CUSTOMER
# ============================================================

def test_anonymous_customer():

    print()
    print("-" * 80)
    print("TEST 8 — ANONYMOUS CUSTOMER")
    print("-" * 80)

    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(),
    )

    result = agent.execute(
        customer_id=None,
        product_id=453,
        product_price=784.23,
        discount_percent=10,
        execute_payment=True,
    )

    check(
        result["customer"]["customer_id"] is None,
        "Anonymous customer has no ID"
    )

    check(
        result["customer"]["known_customer"] is False,
        "Anonymous customer marked correctly"
    )

    check(
        result["checkout"] is not None,
        "Anonymous checkout succeeds"
    )

    check(
        result["razorpay_order"] is not None,
        "Anonymous Razorpay order can be prepared"
    )


# ============================================================
# TEST 9 — FAILURE MATRIX
# ============================================================

class FailingRazorpayClient:

    def create_order(
        self,
        *,
        amount,
        currency="INR",
        receipt=None,
        notes=None,
    ):

        return type(
            "FailedRazorpayOrder",
            (),
            {
                "success": False,
                "status": "RAZORPAY_ORDER_FAILED",
                "razorpay_order_id": None,
                "amount": amount,
                "amount_in_paise": int(round(amount * 100)),
                "currency": currency,
                "receipt": receipt,
                "razorpay_status": "failed",
                "reason": "razorpay_order_creation_failed",
            },
        )()


def test_failure_matrix():

    print()
    print("-" * 80)
    print("TEST 9 — FAILURE MATRIX")
    print("-" * 80)

    # invalid signature
    verifier = PaymentVerifier(key_secret="secret")
    invalid = verifier.verify_payment_signature(
        razorpay_order_id="order_123",
        razorpay_payment_id="pay_123",
        razorpay_signature="bad-signature",
    )
    check(
        invalid.valid is False,
        "Invalid payment signature is rejected"
    )

    # wrong Razorpay order ID
    tx_repo = TransactionRepository()
    tx_repo.upsert({
        "transaction_id": "TRX-FAIL-ORDER-ID",
        "customer_id": 2100,
        "product_id": 10,
        "original_price": 200.0,
        "negotiated_price": 200.0,
        "final_price": 200.0,
        "discount_percent": 0,
        "currency": "INR",
        "status": "PAYMENT_PENDING",
        "payment_status": "PENDING",
        "razorpay_order_id": "order_OK",
        "checkout_ready": True,
    })
    agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(valid=True),
    )
    wrong_order = agent.verify_payment(
        customer_id=2100,
        transaction_id="TRX-FAIL-ORDER-ID",
        product_id=10,
        product_price=200,
        discount_percent=0,
        razorpay_order_id="order_WRONG",
        razorpay_payment_id="pay_abc",
        razorpay_signature="valid-signature",
    )
    check(
        wrong_order["final_action"] == "PAYMENT_VERIFICATION_FAILED",
        "Wrong Razorpay order ID is rejected"
    )

    # wrong payment ID / invalid signature
    bad_payment = agent.verify_payment(
        customer_id=2100,
        transaction_id="TRX-FAIL-ORDER-ID",
        product_id=10,
        product_price=200,
        discount_percent=0,
        razorpay_order_id="order_OK",
        razorpay_payment_id="pay_WRONG",
        razorpay_signature="invalid-signature",
    )
    check(
        bad_payment["payment_verification"]["valid"] is False,
        "Wrong payment ID is rejected during verification"
    )

    # wrong amount is ignored and server uses persisted amount
    tx_repo.upsert({
        "transaction_id": "TRX-FAIL-AMOUNT",
        "customer_id": 2101,
        "product_id": 11,
        "original_price": 500.0,
        "negotiated_price": 500.0,
        "final_price": 450.0,
        "discount_percent": 10,
        "currency": "INR",
        "status": "PAYMENT_PENDING",
        "payment_status": "PENDING",
        "razorpay_order_id": "order_AMOUNT_OK",
        "checkout_ready": True,
    })
    amount_result = agent.verify_payment(
        customer_id=2101,
        transaction_id="TRX-FAIL-AMOUNT",
        product_id=11,
        product_price=99999,
        discount_percent=99,
        razorpay_order_id="order_AMOUNT_OK",
        razorpay_payment_id="pay_AMOUNT_OK",
        razorpay_signature="valid-signature",
    )
    check(
        amount_result["order"]["amount"] == 450.0,
        "Server-authoritative amount wins over client price payload"
    )

    # transaction not found
    missing_tx = agent.verify_payment(
        customer_id=None,
        transaction_id="TRX-NOT-FOUND",
        product_id=11,
        product_price=450,
        discount_percent=10,
        razorpay_order_id="order_MISSING",
        razorpay_payment_id="pay_MISSING",
        razorpay_signature="valid-signature",
    )
    check(
        missing_tx["final_action"] == "EXECUTION_FAILED",
        "Missing transaction is rejected"
    )

    # payment already processed
    webhook_service = WebhookService()
    order_repo = OrderRepository()
    tx_repo.upsert({
        "transaction_id": "TRX-PAYMENT-PROCESSED",
        "customer_id": 2102,
        "product_id": 12,
        "original_price": 250.0,
        "negotiated_price": 250.0,
        "final_price": 250.0,
        "discount_percent": 0,
        "currency": "INR",
        "status": "PAYMENT_PENDING",
        "payment_status": "PENDING",
        "razorpay_order_id": "order_PROCESSED",
        "checkout_ready": True,
    })
    first_verify = agent.verify_payment(
        customer_id=2102,
        transaction_id="TRX-PAYMENT-PROCESSED",
        product_id=12,
        product_price=250,
        discount_percent=0,
        razorpay_order_id="order_PROCESSED",
        razorpay_payment_id="pay_PROCESSED",
        razorpay_signature="valid-signature",
    )
    second_verify = agent.verify_payment(
        customer_id=2102,
        transaction_id="TRX-PAYMENT-PROCESSED",
        product_id=12,
        product_price=250,
        discount_percent=0,
        razorpay_order_id="order_PROCESSED",
        razorpay_payment_id="pay_PROCESSED",
        razorpay_signature="valid-signature",
    )
    stored_same_payment = list(order_repo.collection.find({
        "payment_transaction_id": "pay_PROCESSED"
    }, {"_id": 0}))
    check(
        first_verify["final_action"] == "ORDER_CREATED",
        "First verification creates the order"
    )
    check(
        second_verify["final_action"] == "ORDER_CREATED",
        "Second verification remains idempotent"
    )
    check(
        len(stored_same_payment) == 1,
        "Processed payment creates only one internal order"
    )

    # duplicate webhook
    duplicate_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_DUPLICATE_WEBHOOK",
                    "order_id": "order_DUPLICATE_WEBHOOK",
                    "status": "captured",
                }
            }
        }
    }
    duplicate_result_1 = webhook_service.process(
        webhook_result=type(
            "Result",
            (),
            {
                "valid": True,
                "status": "WEBHOOK_ACCEPTED",
                "event": "payment.captured",
                "event_id": "evt_duplicate_001",
                "razorpay_payment_id": "pay_DUPLICATE_WEBHOOK",
                "razorpay_order_id": "order_DUPLICATE_WEBHOOK",
                "payment_status": "captured",
                "reason": "webhook_verified_successfully",
            },
        )(),
        raw_payload=duplicate_payload,
    )
    duplicate_result_2 = webhook_service.process(
        webhook_result=type(
            "Result",
            (),
            {
                "valid": True,
                "status": "WEBHOOK_ACCEPTED",
                "event": "payment.captured",
                "event_id": "evt_duplicate_001",
                "razorpay_payment_id": "pay_DUPLICATE_WEBHOOK",
                "razorpay_order_id": "order_DUPLICATE_WEBHOOK",
                "payment_status": "captured",
                "reason": "webhook_verified_successfully",
            },
        )(),
        raw_payload=duplicate_payload,
    )
    check(
        duplicate_result_1["status"] == "WEBHOOK_PROCESSED",
        "First duplicate webhook is processed"
    )
    check(
        duplicate_result_2["status"] == "WEBHOOK_DUPLICATE",
        "Duplicate webhook is rejected without creating a second order"
    )

    # malformed webhook
    malformed = RazorpayWebhookHandler().handle(
        raw_body="{not-json",
        signature="sig",
        event_id="evt_malformed_001",
    )
    check(
        malformed.status == "WEBHOOK_REJECTED",
        "Malformed webhook is rejected"
    )
    check(
        malformed.reason == "invalid_webhook_payload",
        "Malformed payload reports the correct reason"
    )

    # invalid webhook signature
    invalid_webhook = RazorpayWebhookHandler().handle(
        raw_body='{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_new","order_id":"order_new","status":"captured"}}}}',
        signature='bad-signature',
        event_id='evt_invalid_sig_001',
    )
    check(
        invalid_webhook.valid is False,
        "Invalid webhook signature is rejected"
    )

    # Razorpay order creation failure
    failing_agent = CommerceExecutionAgent(
        razorpay_client=FailingRazorpayClient(),
        payment_verifier=FakePaymentVerifier(valid=True),
    )
    failed_order = failing_agent.execute(
        customer_id=2200,
        product_id=20,
        product_price=100,
        discount_percent=0,
        payment_method="CARD",
        execute_payment=True,
    )
    check(
        failed_order["final_action"] == "RAZORPAY_ORDER_FAILED",
        "Razorpay order creation failure is surfaced cleanly"
    )

    # MongoDB failure is handled without crashing
    mongo_agent = CommerceExecutionAgent(
        razorpay_client=FakeRazorpayClient(),
        payment_verifier=FakePaymentVerifier(valid=True),
    )
    with patch.object(mongo_agent.order_repository, "create", side_effect=RuntimeError("mongo_down")):
        mongo_result = mongo_agent.verify_payment(
            customer_id=2201,
            transaction_id="TRX-MONGO-FAIL",
            product_id=21,
            product_price=100,
            discount_percent=0,
            razorpay_order_id="order_MONGO_FAIL",
            razorpay_payment_id="pay_MONGO_FAIL",
            razorpay_signature="valid-signature",
        )
    check(
        mongo_result["final_action"] == "ORDER_FAILED",
        "MongoDB write failure does not crash verification"
    )

    # frontend closes payment window = no signature / no payment id
    no_payment = agent.verify_payment(
        customer_id=2100,
        transaction_id="TRX-FAIL-ORDER-ID",
        product_id=10,
        product_price=200,
        discount_percent=0,
        razorpay_order_id="order_OK",
        razorpay_payment_id="",
        razorpay_signature="",
    )
    check(
        no_payment["payment_verification"]["valid"] is False,
        "Payment cancellation / closed window is rejected cleanly"
    )

    # payment failure path
    failed_payment = agent.execute(
        customer_id=2300,
        product_id=30,
        product_price=100,
        discount_percent=0,
        payment_method="CARD",
        execute_payment=True,
        simulate_failure=True,
    )
    check(
        failed_payment["final_action"] == "PAYMENT_FAILED",
        "Explicit payment failure is surfaced"
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():

    print("=" * 80)
    print("AGENTCOMMERCE OS")
    print(
        "PHASE 08D — COMMERCE EXECUTION RAZORPAY TEST SUITE"
    )
    print("=" * 80)

    test_checkout_only()
    test_razorpay_order_creation()
    test_payment_verification_success()
    test_invalid_payment_signature()
    test_price_consistency()
    test_execution_trace()
    test_invalid_price()
    test_anonymous_customer()

    print()
    print("=" * 80)
    print("PHASE 08D RAZORPAY EXECUTION TEST SUMMARY")
    print("=" * 80)

    print(
        f"Total tests : {total_tests}"
    )

    print(
        f"Passed      : {passed_tests}"
    )

    print(
        f"Failed      : {total_tests - passed_tests}"
    )

    print()

    if total_tests == passed_tests:

        print("=" * 80)
        print(
            "ALL PHASE 08D RAZORPAY EXECUTION TESTS PASSED"
        )
        print("=" * 80)

    else:

        print("=" * 80)
        print(
            "SOME PHASE 08D RAZORPAY EXECUTION TESTS FAILED"
        )
        print("=" * 80)

        raise SystemExit(1)


if __name__ == "__main__":
    main()

