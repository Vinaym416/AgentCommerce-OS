#     """
# AGENTCOMMERCE OS
# PHASE 08A — RAZORPAY CLIENT TEST SUITE

# These tests DO NOT call the real Razorpay API.

# The HTTP session is mocked so we can verify:

# - amount conversion
# - currency normalization
# - credentials validation
# - request construction
# - successful order creation
# - API failures
# - connection failures
# - missing order ID
# - order fetching
# """

import sys
from pathlib import Path

import requests


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(ROOT)
    )


from script.payment.razorpay_client import (
    RazorpayClient,
)


# ============================================================
# MOCK RESPONSE
# ============================================================

class MockResponse:

    def __init__(
        self,
        data,
        status_code=200,
        text="",
    ):

        self._data = data

        self.status_code = (
            status_code
        )

        self.text = text

    @property
    def ok(self):

        return (
            200
            <= self.status_code
            < 300
        )

    def json(self):

        return self._data


# ============================================================
# MOCK SESSION
# ============================================================

class MockSession:

    def __init__(
        self,
        post_response=None,
        get_response=None,
        post_exception=None,
        get_exception=None,
    ):

        self.post_response = (
            post_response
        )

        self.get_response = (
            get_response
        )

        self.post_exception = (
            post_exception
        )

        self.get_exception = (
            get_exception
        )

        self.last_post = None

        self.last_get = None

    def post(
        self,
        url,
        auth,
        json,
        timeout,
    ):

        self.last_post = {

            "url": url,

            "auth": auth,

            "json": json,

            "timeout": timeout,

        }

        if self.post_exception:

            raise self.post_exception

        return self.post_response

    def get(
        self,
        url,
        auth,
        timeout,
    ):

        self.last_get = {

            "url": url,

            "auth": auth,

            "timeout": timeout,

        }

        if self.get_exception:

            raise self.get_exception

        return self.get_response


# ============================================================
# TEST HELPER
# ============================================================

def check(
    condition,
    message,
):

    if condition:

        print(
            f"[PASS] {message}"
        )

    else:

        print(
            f"[FAIL] {message}"
        )

        raise AssertionError(
            message
        )


# ============================================================
# TEST 1
# ============================================================

def test_client_initializes():

    client = RazorpayClient(

        key_id="rzp_test_KEY",

        key_secret="TEST_SECRET",

    )

    check(
        client.key_id
        == "rzp_test_KEY",

        "Key ID preserved",
    )

    check(
        client.key_secret
        == "TEST_SECRET",

        "Key secret preserved",
    )


# ============================================================
# TEST 2
# ============================================================

def test_credentials_missing():

    client = RazorpayClient(
        key_id="",
        key_secret=""
    )

    result = client.create_order(
        amount=705.81,
        currency="INR"
    )

    check(
        result.success is False,
        "Missing credentials rejected"
    )

    check(
        result.reason == "razorpay_credentials_missing",
        "Correct missing credential reason"
    )

    client = RazorpayClient(

        key_id=None,

        key_secret=None,

    )

    result = client.create_order(

        amount=705.81

    )

    check(

        result.success is False,

        "Missing credentials rejected",

    )

    check(

        result.reason
        == "razorpay_credentials_missing",

        "Correct missing credential reason",

    )


# ============================================================
# TEST 3
# ============================================================

def test_zero_amount_rejected():

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

    )

    result = client.create_order(

        amount=0

    )

    check(

        result.success is False,

        "Zero amount rejected",

    )

    check(

        result.reason
        == "amount_must_be_positive",

        "Correct zero amount reason",

    )


# ============================================================
# TEST 4
# ============================================================

def test_negative_amount_rejected():

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

    )

    result = client.create_order(

        amount=-100

    )

    check(

        result.success is False,

        "Negative amount rejected",

    )

    check(

        result.reason
        == "amount_must_be_positive",

        "Correct negative amount reason",

    )


# ============================================================
# TEST 5
# ============================================================

def test_invalid_amount_rejected():

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

    )

    result = client.create_order(

        amount="abc"

    )

    check(

        result.success is False,

        "Invalid amount rejected",

    )

    check(

        result.reason
        == "invalid_amount",

        "Correct invalid amount reason",

    )


# ============================================================
# TEST 6
# ============================================================

def test_currency_normalized():

    mock_session = MockSession(

        post_response=MockResponse({

            "id": "order_TEST123",

            "amount": 70581,

            "currency": "INR",

            "receipt": "TEST-001",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81,

        currency="inr",

    )

    check(

        result.success is True,

        "Lowercase currency accepted",

    )

    check(

        result.currency == "INR",

        "Currency normalized to uppercase",

    )


# ============================================================
# TEST 7
# ============================================================

def test_amount_converted_to_paise():

    mock_session = MockSession(

        post_response=MockResponse({

            "id": "order_TEST123",

            "amount": 70581,

            "currency": "INR",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81,

    )

    check(

        result.amount_in_paise == 70581,

        "INR amount converted to paise",

    )

    check(

        mock_session.last_post["json"]["amount"]
        == 70581,

        "API request contains paise amount",

    )


# ============================================================
# TEST 8
# ============================================================

def test_successful_order_creation():

    mock_session = MockSession(

        post_response=MockResponse({

            "id": "order_RAZORPAY123",

            "amount": 70581,

            "amount_paid": 0,

            "amount_due": 70581,

            "currency": "INR",

            "receipt": "AGENT-001",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="rzp_test_KEY",

        key_secret="TEST_SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81,

        currency="INR",

        receipt="AGENT-001",

    )

    check(

        result.success is True,

        "Razorpay order creation succeeds",

    )

    check(

        result.status
        == "RAZORPAY_ORDER_CREATED",

        "Correct success status",

    )

    check(

        result.razorpay_order_id
        == "order_RAZORPAY123",

        "Razorpay order ID returned",

    )

    check(

        result.amount == 705.81,

        "Original amount preserved",

    )

    check(

        result.amount_in_paise == 70581,

        "Paise amount preserved",

    )

    check(

        result.razorpay_status
        == "created",

        "Razorpay order status preserved",

    )


# ============================================================
# TEST 9
# ============================================================

def test_basic_auth_used():

    mock_session = MockSession(

        post_response=MockResponse({

            "id": "order_AUTH123",

            "amount": 10000,

            "currency": "INR",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="MY_KEY",

        key_secret="MY_SECRET",

        session=mock_session,

    )

    client.create_order(

        amount=100

    )

    check(

        mock_session.last_post["auth"]
        == (
            "MY_KEY",
            "MY_SECRET",
        ),

        "Razorpay Basic Auth credentials used",

    )


# ============================================================
# TEST 10
# ============================================================

def test_receipt_and_notes_sent():

    mock_session = MockSession(

        post_response=MockResponse({

            "id": "order_NOTES123",

            "amount": 50000,

            "currency": "INR",

            "receipt": "RECEIPT-001",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    client.create_order(

        amount=500,

        receipt="RECEIPT-001",

        notes={

            "product_id": "453",

            "customer_id": "5176",

        },

    )

    payload = (
        mock_session.last_post["json"]
    )

    check(

        payload["receipt"]
        == "RECEIPT-001",

        "Receipt included in request",

    )

    check(

        payload["notes"]["product_id"]
        == "453",

        "Notes included in request",

    )


# ============================================================
# TEST 11
# ============================================================

def test_api_failure():

    mock_session = MockSession(

        post_response=MockResponse(

            {

                "error": {

                    "code":
                    "BAD_REQUEST_ERROR",

                    "description":
                    "Invalid request",

                }

            },

            status_code=400,

        )

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81

    )

    check(

        result.success is False,

        "Razorpay API failure handled",

    )

    check(

        result.status
        == "RAZORPAY_ORDER_FAILED",

        "Correct API failure status",

    )

    check(

        result.reason
        == "razorpay_api_error",

        "Correct API failure reason",

    )


# ============================================================
# TEST 12
# ============================================================

def test_connection_failure():

    mock_session = MockSession(

        post_exception=requests.RequestException(
            "Connection failed"
        )

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81

    )

    check(

        result.success is False,

        "Connection failure handled",

    )

    check(

        result.reason
        == "razorpay_connection_error",

        "Correct connection failure reason",

    )


# ============================================================
# TEST 13
# ============================================================

def test_missing_order_id():

    mock_session = MockSession(

        post_response=MockResponse({

            "amount": 70581,

            "currency": "INR",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.create_order(

        amount=705.81

    )

    check(

        result.success is False,

        "Missing Razorpay order ID rejected",

    )

    check(

        result.reason
        == "razorpay_order_id_missing",

        "Correct missing order ID reason",

    )


# ============================================================
# TEST 14
# ============================================================

def test_fetch_order():

    mock_session = MockSession(

        get_response=MockResponse({

            "id": "order_FETCH123",

            "amount": 70581,

            "amount_paid": 0,

            "amount_due": 70581,

            "currency": "INR",

            "receipt": "FETCH-001",

            "status": "created",

        })

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.fetch_order(

        "order_FETCH123"

    )

    check(

        result.success is True,

        "Razorpay order fetch succeeds",

    )

    check(

        result.razorpay_order_id
        == "order_FETCH123",

        "Fetched order ID preserved",

    )

    check(

        result.amount == 705.81,

        "Fetched amount converted from paise",

    )

    check(

        result.amount_in_paise
        == 70581,

        "Fetched paise amount preserved",

    )

    check(

        result.razorpay_status
        == "created",

        "Fetched Razorpay status preserved",

    )


# ============================================================
# TEST 15
# ============================================================

def test_fetch_without_order_id():

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

    )

    result = client.fetch_order("")

    check(

        result.success is False,

        "Missing order ID rejected during fetch",

    )

    check(

        result.reason
        == "razorpay_order_id_required",

        "Correct fetch validation reason",

    )


# ============================================================
# TEST 16
# ============================================================

def test_fetch_api_failure():

    mock_session = MockSession(

        get_response=MockResponse(

            {

                "error": {

                    "code":
                    "BAD_REQUEST_ERROR",

                }

            },

            status_code=400,

        )

    )

    client = RazorpayClient(

        key_id="KEY",

        key_secret="SECRET",

        session=mock_session,

    )

    result = client.fetch_order(

        "order_INVALID"

    )

    check(

        result.success is False,

        "Fetch API failure handled",

    )

    check(

        result.reason
        == "razorpay_api_error",

        "Correct fetch API failure reason",

    )


# ============================================================
# RUN ALL TESTS
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS"
    )

    print(
        "PHASE 08A — RAZORPAY CLIENT TEST SUITE"
    )

    print("=" * 80)

    tests = [

        test_client_initializes,

        test_credentials_missing,

        test_zero_amount_rejected,

        test_negative_amount_rejected,

        test_invalid_amount_rejected,

        test_currency_normalized,

        test_amount_converted_to_paise,

        test_successful_order_creation,

        test_basic_auth_used,

        test_receipt_and_notes_sent,

        test_api_failure,

        test_connection_failure,

        test_missing_order_id,

        test_fetch_order,

        test_fetch_without_order_id,

        test_fetch_api_failure,

    ]

    passed = 0

    failed = 0

    for test in tests:

        print()

        try:

            test()

            passed += 1

        except Exception as exc:

            failed += 1

            print(
                f"[FAIL] "
                f"{test.__name__}: "
                f"{exc}"
            )

    print()

    print("=" * 80)

    print(
        "PHASE 08A RAZORPAY CLIENT TEST SUMMARY"
    )

    print("=" * 80)

    print(
        f"Total tests : {len(tests)}"
    )

    print(
        f"Passed      : {passed}"
    )

    print(
        f"Failed      : {failed}"
    )

    print("=" * 80)

    if failed == 0:

        print(
            "ALL PHASE 08A RAZORPAY CLIENT "
            "TESTS PASSED"
        )

    else:

        print(
            "PHASE 08A TESTS FAILED"
        )

        raise SystemExit(1)


if __name__ == "__main__":

    main()