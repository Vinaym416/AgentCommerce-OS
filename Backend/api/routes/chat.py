from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict

from script.agents.commerce_agent import CommerceAgent
from script.context.chat_session_store import ChatSessionStore

router = APIRouter(tags=["Commerce"])
session_store = ChatSessionStore()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    transaction_id: Optional[str] = None
    quantity: int = 1
    negotiation_requested: bool = False
    button_action: Optional[str] = None


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


@router.get("/chat/session/{session_id}")
def get_chat_session(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@router.post("/chat")
def chat(request: ChatRequest):

    try:
        agent = CommerceAgent()
        result = agent.process(
            message=request.message,
            customer_id=request.customer_id,
            quantity=request.quantity,
            product_id=request.product_id,
            transaction_id=request.transaction_id,
            negotiation_requested=request.negotiation_requested,
            button_action=request.button_action,
            session_id=request.session_id,
            execute_payment=False,
        )
        response = {
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
            "customer_intent": result.get("customer_intent"),
            "trace": result.get("agent_trace") or result.get("trace", []),
        }
        if request.session_id:
            session_store.append_turn(
                request.session_id,
                request.customer_id,
                request.model_dump(),
                response,
            )
        return response

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