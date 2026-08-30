"""
AGENTCOMMERCE OS
PHASE 13 — ORDER SERVICE

Coordinates:

Successful Payment
        ↓
Order Agent
        ↓
Order Repository
        ↓
Internal Commerce Order

The OrderService owns orchestration.

The OrderAgent owns validation/business rules.

The OrderRepository owns persistence.
"""

from typing import Any, Dict, Optional

from script.agents.order_agent import (
    OrderAgent,
)

from script.database.repositories.order_repository import (
    OrderRepository,
)


class OrderService:

    def __init__(
        self,
        order_agent: Optional[OrderAgent] = None,
        order_repository: Optional[OrderRepository] = None,
    ):

        self.order_agent = (
            order_agent
            or OrderAgent()
        )

        self.order_repository = (
            order_repository
            or OrderRepository()
        )

    # ========================================================
    # CREATE ORDER AFTER PAYMENT
    # ========================================================

    def create_order_after_payment(
        self,
        *,
        customer_id: int,
        product_id: int,
        amount: float,
        currency: str,
        payment_transaction_id: str,
        payment_status: str = "SUCCESS",
        razorpay_payment_id: Optional[str] = None,
        razorpay_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        # ----------------------------------------------------
        # PAYMENT VALIDATION
        # ----------------------------------------------------

        if payment_status != "SUCCESS":

            return {
                "success": False,
                "status":
                    "ORDER_NOT_CREATED",
                "reason":
                    "order_requires_successful_payment",
            }

        # ----------------------------------------------------
        # IDEMPOTENCY CHECK
        # ----------------------------------------------------

        existing = (
            self.order_repository
            .find_by_payment_transaction_id(
                payment_transaction_id
            )
        )

        if existing:

            return {
                "success": True,
                "status":
                    "ORDER_ALREADY_EXISTS",
                "duplicate": True,
                "order": existing,
                "reason":
                    "order_already_created_for_payment",
            }

        # ----------------------------------------------------
        # BUSINESS VALIDATION
        # ----------------------------------------------------

        order_result = (
            self.order_agent.create_order(

                customer_id=customer_id,

                product_id=product_id,

                amount=amount,

                currency=currency,

                payment_status=payment_status,

                payment_transaction_id=(
                    payment_transaction_id
                ),
            )
        )

        # ----------------------------------------------------
        # AGENT REJECTED
        # ----------------------------------------------------

        if order_result.status != "CONFIRMED":

            return {
                "success": False,
                "status":
                    "ORDER_NOT_CREATED",
                "reason":
                    order_result.reason,
            }

        # ----------------------------------------------------
        # PERSIST ORDER
        # ----------------------------------------------------

        order_document = {

            "customer_id":
                order_result.customer_id,

            "product_id":
                order_result.product_id,

            "amount":
                order_result.amount,

            "currency":
                order_result.currency,

            "payment_transaction_id":
                order_result.payment_transaction_id,

            "payment_status":
                order_result.payment_status,

            "payment_provider":
                order_result.payment_provider,

            "razorpay_payment_id":
                razorpay_payment_id,

            "razorpay_order_id":
                razorpay_order_id,

            "status":
                "CONFIRMED",

        }

        repository_result = (
            self.order_repository.create(
                order_document
            )
        )

        # ----------------------------------------------------
        # RACE CONDITION / DUPLICATE
        # ----------------------------------------------------

        if repository_result["duplicate"]:

            existing = (
                self.order_repository
                .find_by_payment_transaction_id(
                    payment_transaction_id
                )
            )

            return {
                "success": True,
                "status":
                    "ORDER_ALREADY_EXISTS",
                "duplicate": True,
                "order": existing,
                "reason":
                    "order_created_by_another_request",
            }

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        return {

            "success": True,

            "status":
                "ORDER_CREATED",

            "duplicate": False,

            "order_id":
                repository_result["order_id"],

            "reason":
                "order_created_after_successful_payment",
        }