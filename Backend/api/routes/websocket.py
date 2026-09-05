import asyncio
import threading
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from api.routes.chat import ChatRequest
from script.agents.commerce_agent import CommerceAgent
from script.context.chat_session_store import ChatSessionStore

router = APIRouter(tags=["Chat WebSocket"])
session_store = ChatSessionStore()
session_agents = {}
session_agents_lock = threading.Lock()


def _format_response(result):
    return {
        "success": True,
        "message": result.get("response") or result.get("message") or "I've processed your request.",
        "action": result.get("action") or result.get("final_action"),
        "final_action": result.get("final_action"),
        "final_offer": result.get("final_offer", False),
        "products": result.get("products", []),
        "suggested_products": result.get("suggested_products", []),
        "offer": result.get("offer"),
        "transaction": result.get("transaction"),
        "checkout": result.get("checkout"),
        "order": result.get("order"),
        "payment": result.get("payment"),
        "customer_intent": result.get("customer_intent"),
        "trace": result.get("agent_trace") or result.get("trace", []),
    }


def _process_session_turn(agent, request, progress_callback=None):
    """Serialize turns for one session; separate sessions remain parallel."""
    session_lock = session_store.get_session_lock(request.session_id)
    with session_lock:
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
            progress_callback=progress_callback,
        )
        response = _format_response(result)
        response["agent_status"] = agent.get_agent_status()
        response["session_id"] = request.session_id
        session_store.append_turn(
            request.session_id,
            request.customer_id,
            request.model_dump(),
            response,
        )
        return response


def _get_session_agent(session_id):
    with session_agents_lock:
        agent = session_agents.get(session_id)
        if agent is None:
            agent = CommerceAgent()
            session_agents[session_id] = agent
        return agent


@router.websocket("/chat/ws")
async def commerce_chat_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()

            try:
                request = ChatRequest.model_validate(payload)
            except ValidationError as exc:
                await websocket.send_json({
                    "success": False,
                    "error": "Invalid chat request.",
                    "detail": exc.errors(),
                })
                continue

            try:
                if not request.session_id:
                    await websocket.send_json({
                        "success": False,
                        "error": "session_id is required.",
                    })
                    continue
                agent = _get_session_agent(request.session_id)
                loop = asyncio.get_running_loop()

                def progress_callback(event):
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "success": True,
                            "type": "agent_progress",
                            "session_id": request.session_id,
                            **event,
                        }),
                        loop,
                    )

                response = await asyncio.to_thread(
                    _process_session_turn,
                    agent,
                    request,
                    progress_callback,
                )
                await websocket.send_json(response)
            except ValueError as exc:
                await websocket.send_json({
                    "success": False,
                    "error": str(exc),
                })
            except Exception:
                traceback.print_exc()
                await websocket.send_json({
                    "success": False,
                    "error": "Commerce agent failed to process the request.",
                })
    except WebSocketDisconnect:
        return
