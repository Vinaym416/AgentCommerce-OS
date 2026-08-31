from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict

from script.agents.commerce_agent import CommerceAgent

router = APIRouter(tags=["Commerce"])


class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    transaction_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    action: Optional[str] = None
    final_action: Optional[str] = None
    products: list = []
    offer: Optional[Dict[str, Any]] = None
    transaction: Optional[Dict[str, Any]] = None
    checkout: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    payment: Optional[Dict[str, Any]] = None
    trace: list = []


@router.post("/chat")
def chat(request: ChatRequest):

    try:
        agent = CommerceAgent()
        result = agent.process(
            message=request.message,
            customer_id=request.customer_id,
            product_id=request.product_id,
            transaction_id=request.transaction_id,
            execute_payment=False,
        )

        return {
            "success": True,
            "message": result.get("response")
            or result.get("message")
            or "I've processed your request.",
            "action": result.get("action") or result.get("final_action"),
            "final_action": result.get("final_action"),
            "products": result.get("products", []),
            "offer": result.get("offer"),
            "transaction": result.get("transaction"),
            "checkout": result.get("checkout"),
            "order": result.get("order"),
            "payment": result.get("payment"),
            "trace": result.get("agent_trace") or result.get("trace", []),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Commerce agent failed to process the request.",
        )