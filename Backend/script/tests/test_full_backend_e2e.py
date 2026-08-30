"""Single end-to-end backend test for the real commerce flow.

This exercises the full business journey using the production agent classes and a
fake Razorpay gateway boundary, so the test runs reliably without external
credentials while still validating the real backend logic.
"""

import hashlib
import hmac
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script.agents.commerce_agent import CommerceAgent
from script.payment.payment_verifier import PaymentVerificationResult
from script.payment.razorpay_client import RazorpayOrderResult
from script.payment.webhook_handler import RazorpayWebhookHandler
from script.transaction.transaction_manager import TransactionManager
from script.transaction.transaction_state import TransactionState
from script.webhook.webhook_service import WebhookService

CUSTOMER_ID = 5176
WEBHOOK_SECRET = "AGENTCOMMERCE_WEBHOOK_SECRET_2026"


class FakeRazorpayClient:
    def __init__(self):
        self.created_orders = []

    def create_order(self, *, amount, currency="INR", receipt=None, notes=None):
        order_id = f"order_e2e_{len(self.created_orders) + 1}"
        self.created_orders.append({
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
            "order_id": order_id,
        })
        return RazorpayOrderResult(
            status="RAZORPAY_ORDER_CREATED",
            success=True,
            razorpay_order_id=order_id,
            amount=amount,
            amount_in_paise=int(round(amount * 100)),
            currency=currency,
            receipt=receipt,
            razorpay_status="created",
            reason="razorpay_order_created",
            raw_response={"id": order_id, "amount": int(round(amount * 100)), "currency": currency},
        )


class FakePaymentVerifier:
    def __init__(self):
        self.valid = True

    def verify_payment_signature(self, *, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        return PaymentVerificationResult(
            status="PAYMENT_VERIFIED",
            valid=True,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            reason="payment_signature_verified",
        )


def _signature(secret: str, order_id: str, payment_id: str) -> str:
    message = f"{order_id}|{payment_id}"
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def test_full_backend_flow_end_to_end():
    """Run the complete commerce flow: recommendation -> offer -> accept -> checkout -> verify -> webhook -> order."""
    agent = CommerceAgent()
    agent.execution_agent.razorpay_client = FakeRazorpayClient()
    agent.execution_agent.payment_verifier = FakePaymentVerifier()
    agent.execution_agent.payment_service.payment_verifier = FakePaymentVerifier()

    offer_result = agent.process(
        message="I want this product with 10% off.",
        customer_id=CUSTOMER_ID,
        execute_payment=False,
    )

    assert isinstance(offer_result, dict)
    assert offer_result.get("final_action") in {"COUNTER_OFFER", "OFFER_REQUESTED"}
    assert offer_result.get("policy") is not None
    assert offer_result.get("products")

    transaction = TransactionManager().get(CUSTOMER_ID)
    assert transaction is not None
    assert transaction.status in {
        TransactionState.OFFER_CREATED,
        TransactionState.COUNTER_OFFERED,
    }

    accepted_result = agent.process(
        message="Yes, I'll take it.",
        customer_id=CUSTOMER_ID,
        payment_method="UPI",
        execute_payment=True,
    )

    assert accepted_result.get("checkout") is not None
    assert accepted_result["checkout"]["status"] == "CHECKOUT_READY"
    assert accepted_result["checkout"]["payment_ready"] is True
    assert accepted_result.get("final_action") == "PAYMENT_PENDING"

    updated_transaction = TransactionManager().get(CUSTOMER_ID)
    assert updated_transaction is not None
    assert updated_transaction.customer_accepted is True
    assert updated_transaction.checkout_ready is True
    assert updated_transaction.razorpay_order_id is not None

    order_id = updated_transaction.razorpay_order_id
    payment_id = f"pay_e2e_{updated_transaction.transaction_id[-6:]}"
    signature = _signature(WEBHOOK_SECRET, order_id, payment_id)

    verification_result = agent.execution_agent.verify_payment(
        customer_id=CUSTOMER_ID,
        transaction_id=updated_transaction.transaction_id,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
    )

    assert verification_result.get("final_action") == "ORDER_CREATED"
    assert verification_result.get("order") is not None
    assert verification_result["order"]["status"] in {"ORDER_CREATED", "CONFIRMED"}
    assert verification_result.get("payment_verification") is not None
    assert verification_result["payment_verification"]["valid"] is True

    final_transaction = TransactionManager().get(CUSTOMER_ID)
    assert final_transaction is not None
    assert final_transaction.status in {
        TransactionState.PAYMENT_CAPTURED,
        TransactionState.ORDER_CREATED,
        TransactionState.COMPLETED,
    }
    assert final_transaction.razorpay_payment_id == payment_id

    raw_payload = {
        "entity": "event",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "captured",
                }
            }
        },
    }
    raw_body = json.dumps(raw_payload, separators=(",", ":"))
    webhook_signature = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()

    event_id = f"evt_e2e_{uuid4().hex[:12]}"
    webhook_result = RazorpayWebhookHandler(webhook_secret=WEBHOOK_SECRET).handle(
        raw_body=raw_body,
        signature=webhook_signature,
        event_id=event_id,
    )

    assert webhook_result.valid is True
    assert webhook_result.status == "WEBHOOK_ACCEPTED"

    webhook_service = WebhookService()
    service_result = webhook_service.process(
        webhook_result=webhook_result,
        raw_payload=raw_payload,
    )

    assert service_result["success"] is True
    assert service_result["status"] == "WEBHOOK_PROCESSED"
    assert service_result["transaction_update"]["success"] is True

    webhook_transaction = TransactionManager().get(CUSTOMER_ID)
    assert webhook_transaction is not None
    assert webhook_transaction.order_id is not None
    assert webhook_transaction.order_id.startswith("ORD-")
    assert webhook_transaction.status in {TransactionState.ORDER_CREATED, TransactionState.COMPLETED}
