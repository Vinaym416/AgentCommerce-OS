import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


SESSION_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "sessions"
)
LEGACY_SESSION_FILE = SESSION_DIR / "chat_sessions.json"


class ChatSessionStore:
    """Small local Redis-compatible session shape for development."""

    _lock = threading.RLock()
    _session_locks: Dict[str, threading.RLock] = {}

    def __init__(self, path: Path = SESSION_DIR):
        self.directory = Path(path)
        if self.directory.name == "chat_sessions.json":
            self.directory = self.directory.parent
        self.directory.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        safe_session_id = Path(str(session_id)).name
        return self.directory / f"{safe_session_id}.json"

    @classmethod
    def get_session_lock(cls, session_id: str) -> threading.RLock:
        with cls._lock:
            return cls._session_locks.setdefault(session_id, threading.RLock())

    def _read(self) -> Dict[str, Any]:
        if not LEGACY_SESSION_FILE.exists():
            return {}
        try:
            return json.loads(LEGACY_SESSION_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session_path = self._session_path(session_id)
            if session_path.exists():
                try:
                    return json.loads(session_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
            return self._read().get(session_id)

    def find_transaction_context(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Find a transaction's latest offer in local session files."""
        target = str(transaction_id)
        with self._lock:
            for session_path in self.directory.glob("*.json"):
                if session_path.name == LEGACY_SESSION_FILE.name:
                    continue
                try:
                    session = json.loads(session_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue

                for message in reversed(session.get("messages", [])):
                    response = message.get("data") or {}
                    transaction = response.get("transaction") or {}
                    offer = response.get("offer") or {}
                    response_transaction_id = (
                        transaction.get("transaction_id")
                        or offer.get("transaction_id")
                    )
                    if str(response_transaction_id) != target:
                        continue
                    products = response.get("products") or []
                    product = response.get("product") or (products[0] if products else offer)
                    return {
                        "session": session,
                        "transaction": transaction,
                        "offer": offer,
                        "product": product or {},
                    }
        return None

    def append_turn(
        self,
        session_id: str,
        customer_id: Optional[int],
        request: Dict[str, Any],
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        with self._lock:
            session_path = self._session_path(session_id)
            session = self.get(session_id) or {
                "session_id": session_id,
                "customer_id": customer_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": [],
                "context": {},
            }
            session["customer_id"] = customer_id
            session["context"] = {
                key: request[key]
                for key in ("product_id", "transaction_id", "quantity", "negotiation_requested")
                if request.get(key) is not None
            }
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            session["messages"].extend([
                {
                    "role": "user",
                    "text": request.get("message", ""),
                },
                {
                    "role": "assistant",
                    "text": response.get("message", ""),
                    "data": response,
                },
            ])
            session_path.write_text(
                json.dumps(session, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return session
