"""
AGENTCOMMERCE OS
PHASE 08A — RAZORPAY CLIENT

Responsible ONLY for communicating with Razorpay.

Architecture:

Commerce Execution Agent
        ↓
RazorpayClient
        ↓
Razorpay Orders API

IMPORTANT:

This class does NOT:
- negotiate discounts
- calculate commerce decisions
- create internal commerce orders
- verify payment signatures
- handle webhooks

Those responsibilities belong to other layers.

Phase 08A responsibility:
- authenticate with Razorpay
- convert INR amount to paise
- create Razorpay orders
- fetch Razorpay orders
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import os

from dotenv import load_dotenv
import requests

_SENTINEL = object()


# ============================================================
# RAZORPAY RESULT
# ============================================================

@dataclass
class RazorpayOrderResult:

    status: str

    success: bool

    razorpay_order_id: Optional[str]

    amount: Optional[float]

    amount_in_paise: Optional[int]

    currency: str

    receipt: Optional[str]

    razorpay_status: Optional[str]

    reason: str

    raw_response: Optional[Dict[str, Any]] = None


# ============================================================
# RAZORPAY CLIENT
# ============================================================

class RazorpayClient:

    BASE_URL = "https://api.razorpay.com/v1"

    DEFAULT_CURRENCY = "INR"

    def __init__(
        self,
        key_id: Optional[str] = _SENTINEL,
        key_secret: Optional[str] = _SENTINEL,
        session: Optional[requests.Session] = None,
    ):

        load_dotenv()

        if key_id is _SENTINEL:
            self.key_id = os.getenv("RAZORPAY_KEY_ID")
        else:
            self.key_id = key_id

        if key_secret is _SENTINEL:
            self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        else:
            self.key_secret = key_secret

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        print(
            "Razorpay Client initialized."
        )

    # ========================================================
    # VALIDATE CREDENTIALS
    # ========================================================

    def _credentials_available(self) -> bool:

        return bool(
            self.key_id
            and self.key_secret
        )

    # ========================================================
    # CONVERT AMOUNT
    # ========================================================

    def _to_paise(
        self,
        amount: float,
    ) -> int:

        return int(
            round(
                float(amount) * 100
            )
        )

    # ========================================================
    # CREATE RAZORPAY ORDER
    # ========================================================

    def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, str]] = None,
    ) -> RazorpayOrderResult:

        # ----------------------------------------------------
        # AMOUNT VALIDATION
        # ----------------------------------------------------

        try:

            numeric_amount = float(amount)

        except (
            TypeError,
            ValueError,
        ):

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=None,

                amount_in_paise=None,

                currency=currency,

                receipt=receipt,

                razorpay_status=None,

                reason="invalid_amount",

            )

        if numeric_amount <= 0:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=numeric_amount,

                amount_in_paise=None,

                currency=currency,

                receipt=receipt,

                razorpay_status=None,

                reason="amount_must_be_positive",

            )

        # ----------------------------------------------------
        # CURRENCY VALIDATION
        # ----------------------------------------------------

        normalized_currency = (
            str(currency)
            .upper()
        )

        if len(normalized_currency) != 3:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=None,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=None,

                reason="invalid_currency",

            )

        # ----------------------------------------------------
        # CREDENTIAL VALIDATION
        # ----------------------------------------------------

        if not self._credentials_available():

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=None,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=None,

                reason="razorpay_credentials_missing",

            )

        # ----------------------------------------------------
        # CONVERT TO SMALLEST CURRENCY UNIT
        # ----------------------------------------------------

        amount_in_paise = self._to_paise(
            numeric_amount
        )

        if amount_in_paise <= 0:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=amount_in_paise,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=None,

                reason="amount_below_minimum_unit",

            )

        # ----------------------------------------------------
        # REQUEST BODY
        # ----------------------------------------------------

        payload: Dict[str, Any] = {

            "amount": amount_in_paise,

            "currency": normalized_currency,

        }

        if receipt is not None:

            payload["receipt"] = str(
                receipt
            )

        if notes:

            payload["notes"] = notes

        # ----------------------------------------------------
        # API REQUEST
        # ----------------------------------------------------

        try:

            response = self.session.post(

                f"{self.BASE_URL}/orders",

                auth=(
                    self.key_id,
                    self.key_secret,
                ),

                json=payload,

                timeout=15,

            )

        except requests.RequestException as exc:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=amount_in_paise,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=None,

                reason="razorpay_connection_error",

                raw_response={
                    "error": str(exc)
                },

            )

        # ----------------------------------------------------
        # PARSE RESPONSE
        # ----------------------------------------------------

        try:

            response_data = response.json()

        except ValueError:

            response_data = {
                "raw_text": response.text
            }

        # ----------------------------------------------------
        # API FAILURE
        # ----------------------------------------------------

        if not response.ok:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=amount_in_paise,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=None,

                reason="razorpay_api_error",

                raw_response=response_data,

            )

        # ----------------------------------------------------
        # ORDER ID VALIDATION
        # ----------------------------------------------------

        razorpay_order_id = response_data.get(
            "id"
        )

        if not razorpay_order_id:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=round(
                    numeric_amount,
                    2
                ),

                amount_in_paise=amount_in_paise,

                currency=normalized_currency,

                receipt=receipt,

                razorpay_status=response_data.get(
                    "status"
                ),

                reason="razorpay_order_id_missing",

                raw_response=response_data,

            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return RazorpayOrderResult(

            status="RAZORPAY_ORDER_CREATED",

            success=True,

            razorpay_order_id=razorpay_order_id,

            amount=round(
                numeric_amount,
                2
            ),

            amount_in_paise=amount_in_paise,

            currency=normalized_currency,

            receipt=response_data.get(
                "receipt",
                receipt,
            ),

            razorpay_status=response_data.get(
                "status"
            ),

            reason="razorpay_order_created_successfully",

            raw_response=response_data,

        )

    # ========================================================
    # FETCH RAZORPAY ORDER
    # ========================================================

    def fetch_order(
        self,
        razorpay_order_id: str,
    ) -> RazorpayOrderResult:

        if not razorpay_order_id:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FETCH_FAILED",

                success=False,

                razorpay_order_id=None,

                amount=None,

                amount_in_paise=None,

                currency=self.DEFAULT_CURRENCY,

                receipt=None,

                razorpay_status=None,

                reason="razorpay_order_id_required",

            )

        if not self._credentials_available():

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FETCH_FAILED",

                success=False,

                razorpay_order_id=razorpay_order_id,

                amount=None,

                amount_in_paise=None,

                currency=self.DEFAULT_CURRENCY,

                receipt=None,

                razorpay_status=None,

                reason="razorpay_credentials_missing",

            )

        # ----------------------------------------------------
        # API REQUEST
        # ----------------------------------------------------

        try:

            response = self.session.get(

                f"{self.BASE_URL}/orders/"
                f"{razorpay_order_id}",

                auth=(
                    self.key_id,
                    self.key_secret,
                ),

                timeout=15,

            )

        except requests.RequestException as exc:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FETCH_FAILED",

                success=False,

                razorpay_order_id=razorpay_order_id,

                amount=None,

                amount_in_paise=None,

                currency=self.DEFAULT_CURRENCY,

                receipt=None,

                razorpay_status=None,

                reason="razorpay_connection_error",

                raw_response={
                    "error": str(exc)
                },

            )

        # ----------------------------------------------------
        # PARSE RESPONSE
        # ----------------------------------------------------

        try:

            response_data = response.json()

        except ValueError:

            response_data = {
                "raw_text": response.text
            }

        # ----------------------------------------------------
        # FAILURE
        # ----------------------------------------------------

        if not response.ok:

            return RazorpayOrderResult(

                status="RAZORPAY_ORDER_FETCH_FAILED",

                success=False,

                razorpay_order_id=razorpay_order_id,

                amount=None,

                amount_in_paise=None,

                currency=self.DEFAULT_CURRENCY,

                receipt=None,

                razorpay_status=None,

                reason="razorpay_api_error",

                raw_response=response_data,

            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        amount_in_paise = response_data.get(
            "amount"
        )

        amount = (
            round(
                amount_in_paise / 100,
                2
            )
            if isinstance(
                amount_in_paise,
                (int, float)
            )
            else None
        )

        return RazorpayOrderResult(

            status="RAZORPAY_ORDER_FETCHED",

            success=True,

            razorpay_order_id=response_data.get(
                "id",
                razorpay_order_id,
            ),

            amount=amount,

            amount_in_paise=amount_in_paise,

            currency=response_data.get(
                "currency",
                self.DEFAULT_CURRENCY,
            ),

            receipt=response_data.get(
                "receipt"
            ),

            razorpay_status=response_data.get(
                "status"
            ),

            reason="razorpay_order_fetched_successfully",

            raw_response=response_data,

        )


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — RAZORPAY CLIENT"
    )

    print("=" * 80)

    client = RazorpayClient()

    print("\n")

    print("-" * 80)

    print("TEST — CREATE RAZORPAY ORDER")

    print("-" * 80)

    result = client.create_order(

        amount=705.81,

        currency="INR",

        receipt="AGENTCOMMERCE-TEST-001",

        notes={
            "product_id": "453",
            "customer_id": "5176",
        },

    )

    print(result)


if __name__ == "__main__":

    main()