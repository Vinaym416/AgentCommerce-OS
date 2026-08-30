"""
AGENTCOMMERCE OS
CHECKOUT SERVICE

Responsible for preparing a transaction for Razorpay payment.

Flow:

Transaction
    ↓
Validate checkout
    ↓
Create Razorpay Order
    ↓
Persist Razorpay Order ID
    ↓
PAYMENT_PENDING
    ↓
Return checkout data
"""

from typing import Any, Dict

from script.transaction.transaction_manager import (
    TransactionManager,
)

from script.payment.razorpay_client import (
    RazorpayClient,
)


class CheckoutService:

    def __init__(
        self,
        transaction_manager=None,
        razorpay_client=None,
    ):

        self.transaction_manager = (
            transaction_manager
            or TransactionManager()
        )

        self.razorpay_client = (
            razorpay_client
            or RazorpayClient()
        )

    # ========================================================
    # CREATE CHECKOUT
    # ========================================================

    def create_checkout(
        self,
        customer_id: int,
    ) -> Dict[str, Any]:

        # ----------------------------------------------------
        # GET TRANSACTION
        # ----------------------------------------------------

        transaction = (
            self.transaction_manager.get(
                customer_id
            )
        )

        if transaction is None:

            return {
                "success": False,
                "status": "CHECKOUT_FAILED",
                "reason": "transaction_not_found",
            }

        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if transaction.product_id is None:

            return {
                "success": False,
                "status": "CHECKOUT_FAILED",
                "reason": "product_id_missing",
            }

        if transaction.final_price <= 0:

            return {
                "success": False,
                "status": "CHECKOUT_FAILED",
                "reason": "invalid_final_price",
            }

        if not transaction.customer_accepted:

            return {
                "success": False,
                "status": "CHECKOUT_FAILED",
                "reason": "customer_acceptance_required",
            }

        # ----------------------------------------------------
        # PREVENT DUPLICATE RAZORPAY ORDER
        # ----------------------------------------------------

        if transaction.razorpay_order_id:

            return {
                "success": True,
                "status": "CHECKOUT_ALREADY_CREATED",

                "transaction_id":
                    transaction.transaction_id,

                "razorpay_order_id":
                    transaction.razorpay_order_id,

                "amount":
                    transaction.final_price,

                "currency":
                    "INR",
            }

        # ----------------------------------------------------
        # CREATE RAZORPAY ORDER
        # ----------------------------------------------------

        amount_paise = int(
            round(
                transaction.final_price * 100
            )
        )

        razorpay_order = (
            self.razorpay_client.create_order(
                amount=amount_paise,
                currency="INR",
                receipt=transaction.transaction_id,
                notes={
                    "transaction_id":
                        transaction.transaction_id,

                    "customer_id":
                        str(transaction.customer_id),

                    "product_id":
                        str(transaction.product_id),
                },
            )
        )

        # ----------------------------------------------------
        # EXTRACT RAZORPAY ORDER ID
        # ----------------------------------------------------

        razorpay_order_id = (
            razorpay_order.get("id")
        )

        if not razorpay_order_id:

            return {
                "success": False,
                "status": "CHECKOUT_FAILED",
                "reason":
                    "razorpay_order_id_missing",
            }

        # ----------------------------------------------------
        # UPDATE TRANSACTION
        # ----------------------------------------------------

        updated = (
            self.transaction_manager
            .create_or_update(

                customer_id=customer_id,

                razorpay_order_id=
                    razorpay_order_id,

                status="PAYMENT_PENDING",

                checkout_ready=True,

                payment_status="PENDING",
            )
        )

        # ----------------------------------------------------
        # RETURN CHECKOUT DATA
        # ----------------------------------------------------

        return {

            "success": True,

            "status":
                "CHECKOUT_CREATED",

            "transaction_id":
                updated.transaction_id,

            "razorpay_order_id":
                razorpay_order_id,

            "amount":
                updated.final_price,

            "amount_paise":
                amount_paise,

            "currency":
                "INR",

            "customer_id":
                updated.customer_id,

            "product_id":
                updated.product_id,
        }