
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
    PaymentVerificationResult
)


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
        product_price=784.23,
        discount_percent=10,
        razorpay_order_id="order_TEST123",
        razorpay_payment_id="pay_TEST456",
        razorpay_signature="valid-signature",
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

