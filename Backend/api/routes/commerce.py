from typing import Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from script.payment.webhook_handler import (
    RazorpayWebhookHandler,
)

from script.webhook.webhook_service import (
    WebhookService,
)
from pydantic import BaseModel

from script.agents.commerce_execution_agent import (
    CommerceExecutionAgent,
)
from script.database.repositories.customer_repository import (
    CustomerRepository,
)
from script.database.repositories.product_repository import (
    ProductRepository,
)
from script.transaction.transaction_manager import TransactionManager
from script.context.chat_session_store import ChatSessionStore
from pymongo.errors import PyMongoError
import threading
import json
router = APIRouter()

_execution_agent = None
_execution_agent_lock = threading.Lock()


def _get_execution_agent():
    global _execution_agent
    if _execution_agent is None:
        with _execution_agent_lock:
            if _execution_agent is None:
                _execution_agent = CommerceExecutionAgent()
    return _execution_agent


# ============================================================
# REQUEST SCHEMA
# ============================================================

class CreatePaymentOrderRequest(BaseModel):

    customer_id: Optional[int] = None

    transaction_id: Optional[str] = None

    product_id: int

    product_price: float

    discount_percent: float = 0.0

    quantity: int = 1


class VerifyPaymentRequest(BaseModel):
    """
    SECURITY: Only transaction_id is accepted.

    Frontend MUST NOT send product data (product_id, product_price, discount_percent).
    Backend retrieves all transaction data from MongoDB using transaction_id only.
    This prevents malicious clients from tampering with pricing during verification.
    """

    transaction_id: str  # REQUIRED - no optional fallback

    razorpay_order_id: Optional[str] = None  # Optional; backend resolves stored order ID

    razorpay_payment_id: str

    razorpay_signature: str


# ============================================================
# GET CURRENT COMMERCE SESSION
# ============================================================

@router.get("/session/{customer_id}")
def get_commerce_session(
    customer_id: int,
    transaction_id: Optional[str] = None,
    quantity: Optional[int] = None,
):
    """
    Return the server-generated offer for a customer/session.
    The frontend must consume this payload instead of hardcoding pricing.
    """

    resolved_customer_id = int(customer_id)
    local_context = (
        ChatSessionStore().find_transaction_context(transaction_id)
        if transaction_id
        else None
    )
    local_transaction = (local_context or {}).get("transaction") or {}
    local_offer = (local_context or {}).get("offer") or {}
    local_product = (local_context or {}).get("product") or local_offer

    customer_repository = CustomerRepository()
    product_repository = ProductRepository()

    try:
        customer = customer_repository.get_by_customer_id(resolved_customer_id)
    except PyMongoError:
        customer = None
    if customer is None:
        customer = {
            "customer_id": resolved_customer_id,
            "customer_name": "AgentCommerce Customer",
            "preferred_category": "electronics",
        }

    transaction = None
    if transaction_id:
        try:
            transaction = TransactionManager().get_by_transaction_id(transaction_id)
        except PyMongoError:
            transaction = None
        if transaction and transaction.customer_id != resolved_customer_id:
            raise HTTPException(status_code=404, detail="Checkout transaction not found.")

    product_id = (
        transaction.product_id if transaction
        else local_transaction.get("product_id")
        or local_product.get("product_id")
        or 453
    )
    try:
        product = product_repository.get_by_product_id(product_id)
    except PyMongoError:
        product = None
    if product is None:
        product = local_product or {
            "product_id": 453,
            "name": "Premium Product",
            "current_price": 784.23,
            "category_name": "Premium",
            "avg_rating": 4.6,
        }

    product_id = int(product.get("product_id", product_id))
    if transaction:
        requested_quantity = quantity
        quantity = max(1, int(getattr(transaction, "quantity", 1) or 1))
        if requested_quantity is not None:
            if requested_quantity < 1:
                raise HTTPException(status_code=400, detail="quantity must be at least 1")
            quantity = requested_quantity
        stored_original_price = float(transaction.original_price)
        stored_final_price = float(transaction.final_price)
        payment_started = transaction.status in {
            "PAYMENT_PENDING",
            "PAYMENT_AUTHORIZED",
            "PAYMENT_CAPTURED",
            "ORDER_CREATED",
            "COMPLETED",
        }
        original_price = (
            round(stored_original_price / quantity, 2)
            if payment_started and getattr(transaction, "quantity", 1) > 1
            else stored_original_price
        )
        discount_percent = float(transaction.discount_percent)
        final_price = (
            round(stored_final_price / max(1, int(getattr(transaction, "quantity", 1) or 1)), 2)
            if payment_started and getattr(transaction, "quantity", 1) > 1
            else stored_final_price
        )
    elif local_transaction:
        quantity = max(1, int(local_transaction.get("quantity", quantity or 1) or 1))
        original_price = float(
            local_transaction.get("original_price")
            or local_offer.get("original_price")
            or product.get("current_price")
            or product.get("price")
            or 784.23
        )
        discount_percent = float(
            local_transaction.get("discount_percent")
            or local_offer.get("discount_percent")
            or 0.0
        )
        final_price = float(
            local_transaction.get("final_price")
            or local_offer.get("final_price")
            or original_price * (1 - discount_percent / 100.0)
        )
    else:
        quantity = 1
        original_price = float(product.get("current_price") or product.get("price") or 784.23)
        discount_percent = 10.0
        final_price = round(original_price * (1 - (discount_percent / 100.0)), 2)

    resolved_transaction_id = (
        transaction.transaction_id
        if transaction
        else f"session_{resolved_customer_id}_{product_id}_{int(final_price * 100)}"
    )

    return {
        "transaction_id": resolved_transaction_id,
        "transaction_status": (
            transaction.status
            if transaction else None
        ),
        "payment_status": (
            transaction.payment_status
            if transaction else None
        ),
        "order_id": (
            transaction.order_id
            if transaction else None
        ),
        "product": {
            "product_id": product_id,
            "name": product.get("name", "Premium Product"),
            "category": product.get("category_name") or product.get("category") or "Premium",
            "price": original_price,
        },
        "original_price": original_price,
        "discount": discount_percent,
        "discount_amount": round(original_price - final_price, 2),
        "final_price": final_price,
        "quantity": quantity,
        "total_original_price": round(original_price * quantity, 2),
        "total_discount_amount": round((original_price - final_price) * quantity, 2),
        "total_final_price": round(final_price * quantity, 2),
        "customer": {
            "customer_id": resolved_customer_id,
            "name": customer.get("customer_name", "AgentCommerce Customer"),
            "preferred_category": customer.get("preferred_category", "Premium"),
        },
    }


# ============================================================
# CREATE PAYMENT ORDER
# ============================================================

@router.post("/create-payment-order")
def create_payment_order(
    request: CreatePaymentOrderRequest,
):

    if request.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be at least 1")
    if request.quantity > 10:
        raise HTTPException(status_code=400, detail="quantity must be at most 10")

    agent = _get_execution_agent()

    result = agent.execute(
        customer_id=request.customer_id,
        product_id=request.product_id,
        product_price=request.product_price,
        quantity=request.quantity,
        discount_percent=request.discount_percent,
        transaction_id=request.transaction_id,
        payment_method="RAZORPAY",
        execute_payment=True,
        notes={
            "customer_id": str(request.customer_id or ""),
            "product_id": str(request.product_id),
            "quantity": str(request.quantity),
        },
    )

    # --------------------------------------------------------
    # RAZORPAY ORDER FAILURE
    # --------------------------------------------------------

    if result["final_action"] == "RAZORPAY_ORDER_FAILED":

        raise HTTPException(
            status_code=502,
            detail=result,
        )

    razorpay_order = result.get(
        "razorpay_order"
    )

    if not razorpay_order:

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Razorpay order was not created.",
                "result": result,
            },
        )

    # --------------------------------------------------------
    # RETURN ONLY WHAT FRONTEND NEEDS
    # --------------------------------------------------------

    # --------------------------------------------------------
    # EXTRACT TRANSACTION ID
    # --------------------------------------------------------
    
    transaction_id = None
    if result.get("razorpay_order") and "transaction_id" in result["razorpay_order"]:
        transaction_id = result["razorpay_order"]["transaction_id"]
    
    # If razorpay_order doesn't have transaction_id, check checkout
    if not transaction_id and result.get("checkout") and "transaction_id" in result["checkout"]:
        transaction_id = result["checkout"]["transaction_id"]

    # --------------------------------------------------------
    # RETURN PAYMENT ORDER WITH TRANSACTION ID
    # --------------------------------------------------------

    return {

        "success": True,
        
        "transactionId": transaction_id,  # CRITICAL: Frontend must store this

        "orderId": razorpay_order[
            "razorpay_order_id"
        ],

        "amount": razorpay_order[
            "amount_in_paise"
        ],

        "currency": razorpay_order[
            "currency"
        ],

        "keyId": agent.razorpay_client.key_id,

        "checkout": result["checkout"],

    }


# ============================================================
# VERIFY PAYMENT
# ============================================================

@router.post("/verify-payment")
def verify_payment(
    request: VerifyPaymentRequest,
):

    try:
        agent = _get_execution_agent()
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Payment verification is temporarily unavailable because the database cannot be reached.",
                "reason": str(exc),
            },
        ) from exc

    # SECURITY: Only transaction_id is used. Product data is ignored.
    try:
        result = agent.verify_payment(
            customer_id=None,  # Will be loaded from transaction
            transaction_id=request.transaction_id,  # REQUIRED - single source of truth
            product_id=None,  # NOT USED - ignored for security
            product_price=None,  # NOT USED - ignored for security
            discount_percent=None,  # NOT USED - ignored for security
            razorpay_order_id=request.razorpay_order_id or "",
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature,
        )
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Payment verification is temporarily unavailable because the database cannot be reached.",
                "reason": str(exc),
            },
        ) from exc

    if result["final_action"] in {
        "PAYMENT_VERIFICATION_FAILED",
        "ORDER_FAILED",
    }:
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result






# ============================================================
# RAZORPAY WEBHOOK
# ============================================================

@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
):

    # --------------------------------------------------------
    # RAW BODY
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Razorpay signature verification MUST use
    # the exact raw request body.
    #
    # Do NOT use await request.json()
    # before signature verification.
    #

    raw_body = await request.body()

    # --------------------------------------------------------
    # RAZORPAY HEADERS
    # --------------------------------------------------------

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    event_id = request.headers.get(
        "x-razorpay-event-id"
    )

    # --------------------------------------------------------
    # WEBHOOK SECRET
    # --------------------------------------------------------

    import os

    webhook_secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET"
    )

    # --------------------------------------------------------
    # HANDLER
    # --------------------------------------------------------

    handler = RazorpayWebhookHandler(
        webhook_secret=webhook_secret
    )

    # --------------------------------------------------------
    # DECODE RAW BODY
    # --------------------------------------------------------

    try:

        raw_body_text = raw_body.decode(
            "utf-8"
        )

    except UnicodeDecodeError:

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook body encoding.",
        )

    # --------------------------------------------------------
    # VERIFY WEBHOOK
    # --------------------------------------------------------

    webhook_result = handler.handle(

        raw_body=raw_body_text,

        signature=signature,

        event_id=event_id,

    )

    # --------------------------------------------------------
    # REJECT INVALID WEBHOOK
    # --------------------------------------------------------

    if not webhook_result.valid:

        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "status": webhook_result.status,
                "reason": webhook_result.reason,
            },
        )

    # --------------------------------------------------------
    # PARSE JSON ONLY AFTER SIGNATURE VERIFICATION
    # --------------------------------------------------------

    try:

        payload = json.loads(raw_body_text)

    except (TypeError, ValueError, json.JSONDecodeError):

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON payload.",
        )

    # --------------------------------------------------------
    # PROCESS EVENT
    # --------------------------------------------------------

    service = WebhookService()

    result = service.process(

        webhook_result=webhook_result,

        raw_payload=payload,

    )

    # --------------------------------------------------------
    # RETURN 200
    # --------------------------------------------------------

    return result