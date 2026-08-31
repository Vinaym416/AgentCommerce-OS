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
import json
router = APIRouter()


# ============================================================
# REQUEST SCHEMA
# ============================================================

class CreatePaymentOrderRequest(BaseModel):

    customer_id: Optional[int] = None

    transaction_id: Optional[str] = None

    product_id: int

    product_price: float

    discount_percent: float = 0.0


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
):
    """
    Return the server-generated offer for a customer/session.
    The frontend must consume this payload instead of hardcoding pricing.
    """

    customer_repository = CustomerRepository()
    product_repository = ProductRepository()

    resolved_customer_id = int(customer_id)

    customer = customer_repository.get_by_customer_id(resolved_customer_id)
    if customer is None:
        customer = {
            "customer_id": resolved_customer_id,
            "customer_name": "AgentCommerce Customer",
            "preferred_category": "electronics",
        }

    transaction = None
    if transaction_id:
        transaction = TransactionManager().get_by_transaction_id(transaction_id)
        if transaction and transaction.customer_id != resolved_customer_id:
            raise HTTPException(status_code=404, detail="Checkout transaction not found.")

    product_id = transaction.product_id if transaction else 453
    product = product_repository.get_by_product_id(product_id)
    if product is None:
        product = {
            "product_id": 453,
            "name": "Premium Product",
            "current_price": 784.23,
            "category_name": "Premium",
            "avg_rating": 4.6,
        }

    product_id = int(product.get("product_id", product_id))
    if transaction:
        original_price = float(transaction.original_price)
        discount_percent = float(transaction.discount_percent)
        final_price = float(transaction.final_price)
    else:
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

    agent = CommerceExecutionAgent()

    result = agent.execute(
        customer_id=request.customer_id,
        product_id=request.product_id,
        product_price=request.product_price,
        discount_percent=request.discount_percent,
        transaction_id=request.transaction_id,
        payment_method="RAZORPAY",
        execute_payment=True,
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

    agent = CommerceExecutionAgent()

    # SECURITY: Only transaction_id is used. Product data is ignored.
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