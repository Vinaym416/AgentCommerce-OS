"""
AGENTCOMMERCE OS
PHASE 05 — AGENT SESSION MEMORY

This is the short-term context store for the agent workflow.

Requested contract:
- Input: {session_id, customer_id, key, value, ttl_seconds}
- Output: {status, data}

In production this should be backed by Redis for fast, TTL-based session storage.
"""

import time
from typing import Any, Dict, Optional


class CustomerMemoryScope:
    """Single customer's conversation memory."""

    def __init__(self):
        self.last_message = None
        self.last_intent = None
        self.last_products = []
        self.selected_product = None
        self.last_merchant_decision = None
        self.last_negotiation_result = None
        self.last_policy_result = None
        self.pending_offer = None
        self.session_store = {}


class AgentMemory:
    """Customer-scoped conversation memory manager with TTL-backed session values."""

    def __init__(self, default_ttl_seconds: int = 600):
        self.scopes = {}
        self.customer_id = None
        self.last_message = None
        self.last_intent = None
        self.last_products = []
        self.selected_product = None
        self.last_merchant_decision = None
        self.last_negotiation_result = None
        self.last_policy_result = None
        self.pending_offer = None
        self.store = {}
        self.default_ttl_seconds = default_ttl_seconds

    def _get_scope(self, customer_id=None, session_id=None):
        if session_id is not None:
            if session_id not in self.scopes:
                self.scopes[session_id] = CustomerMemoryScope()
            return self.scopes[session_id]

        if customer_id is None:
            return self

        if customer_id not in self.scopes:
            self.scopes[customer_id] = CustomerMemoryScope()
        return self.scopes[customer_id]

    def set_customer(self, customer_id):
        self.customer_id = customer_id

    def set_session_value(
        self,
        *,
        session_id: str,
        customer_id: Optional[int],
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Store a value in the session memory with time-to-live."""
        ttl = self.default_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        expires_at = time.time() + ttl

        if session_id not in self.store:
            self.store[session_id] = {}

        self.store[session_id][key] = {
            "customer_id": customer_id,
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at,
            "ttl_seconds": ttl,
        }

        if customer_id is not None:
            self.customer_id = customer_id

        return {"status": "SUCCESS", "data": value}

    def get_session_value(
        self,
        *,
        session_id: str,
        customer_id: Optional[int] = None,
        key: str = "",
    ) -> Dict[str, Any]:
        """Fetch a value from the session memory; returns the requested contract."""
        session_data = self.store.get(session_id, {})
        entry = session_data.get(key)

        if entry is None:
            return {"status": "NOT_FOUND", "data": None}

        if entry.get("expires_at", 0) <= time.time():
            del session_data[key]
            return {"status": "EXPIRED", "data": None}

        if customer_id is not None and entry.get("customer_id") not in (None, customer_id):
            return {"status": "FORBIDDEN", "data": None}

        return {"status": "SUCCESS", "data": entry["value"]}

    def delete_session_value(
        self,
        *,
        session_id: str,
        customer_id: Optional[int] = None,
        key: str,
    ) -> Dict[str, Any]:
        session_data = self.store.get(session_id, {})
        entry = session_data.get(key)

        if entry is None:
            return {"status": "NOT_FOUND", "data": None}

        if customer_id is not None and entry.get("customer_id") not in (None, customer_id):
            return {"status": "FORBIDDEN", "data": None}

        del session_data[key]
        return {"status": "SUCCESS", "data": None}

    def set_message(self, message, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_message = message
        if customer_id is None:
            self.last_message = message
        return {"status": "SUCCESS", "data": message}

    def get_message(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_message

    def set_intent(self, intent, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_intent = intent
        if customer_id is None:
            self.last_intent = intent
        return {"status": "SUCCESS", "data": intent}

    def get_intent(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_intent

    def set_products(self, products, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_products = products
        if products:
            scope.selected_product = products[0]
        if customer_id is None:
            self.last_products = products
            self.selected_product = products[0] if products else None
        return {"status": "SUCCESS", "data": products}

    def get_products(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_products

    def select_product(self, index=0, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)

        if not scope.last_products:
            return None
        if index < 0 or index >= len(scope.last_products):
            return None

        scope.selected_product = scope.last_products[index]
        if customer_id is None:
            self.selected_product = scope.selected_product
        return scope.selected_product

    def get_selected_product(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).selected_product

    def set_merchant_decision(self, decision, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_merchant_decision = decision
        if customer_id is None:
            self.last_merchant_decision = decision
        return {"status": "SUCCESS", "data": decision}

    def get_merchant_decision(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_merchant_decision

    def set_negotiation_result(self, result, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_negotiation_result = result
        if customer_id is None:
            self.last_negotiation_result = result
        return {"status": "SUCCESS", "data": result}

    def get_negotiation_result(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_negotiation_result

    def set_policy_result(self, result, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_policy_result = result
        if customer_id is None:
            self.last_policy_result = result
        return {"status": "SUCCESS", "data": result}

    def get_policy_result(self, customer_id=None, session_id=None):
        return self._get_scope(customer_id=customer_id, session_id=session_id).last_policy_result

    def set_pending_offer(self, offer, customer_id=None, session_id=None):
        target_session_id = session_id or self.customer_id or "default_session"
        target_customer_id = customer_id if customer_id is not None else self.customer_id
        self.pending_offer = offer
        if target_customer_id is None:
            target_customer_id = self.customer_id
        result = self.set_session_value(
            session_id=target_session_id,
            customer_id=target_customer_id,
            key="pending_offer",
            value=offer,
            ttl_seconds=self.default_ttl_seconds,
        )
        return result

    def get_pending_offer(self, customer_id=None, session_id=None):
        target_session_id = session_id or self.customer_id or "default_session"
        target_customer_id = customer_id if customer_id is not None else self.customer_id
        response = self.get_session_value(
            session_id=target_session_id,
            customer_id=target_customer_id,
            key="pending_offer",
        )
        if response["status"] == "SUCCESS":
            return response["data"]
        return None

    def clear_pending_offer(self, customer_id=None, session_id=None):
        target_session_id = session_id or self.customer_id or "default_session"
        target_customer_id = customer_id if customer_id is not None else self.customer_id
        self.pending_offer = None
        return self.delete_session_value(
            session_id=target_session_id,
            customer_id=target_customer_id,
            key="pending_offer",
        )

    def resolve_product_reference(self, message, customer_id=None, session_id=None):
        """Resolve simple conversational references for a customer."""
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        text = message.lower().strip()

        references = [
            "this product",
            "that product",
            "this one",
            "that one",
            "the product",
            "the item",
        ]

        for reference in references:
            if reference in text:
                return scope.selected_product

        numbered_products = {
            "first": 0,
            "second": 1,
            "third": 2,
            "fourth": 3,
            "fifth": 4,
        }

        for word, index in numbered_products.items():
            if word in text and "product" in text and index < len(scope.last_products):
                return scope.last_products[index]

        return None

    def clear_customer(self, customer_id):
        """Clear all memory for a customer (logout/session end)."""
        if customer_id in self.scopes:
            del self.scopes[customer_id]

    def reset_product_selection(self, customer_id=None, session_id=None):
        """Clear the last product selection for a fresh search."""
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        scope.last_products = []
        scope.selected_product = None
        if customer_id is None:
            self.last_products = []
            self.selected_product = None

    def snapshot(self, customer_id=None, session_id=None):
        scope = self._get_scope(customer_id=customer_id, session_id=session_id)
        selected = scope.selected_product

        return {
            "customer_id": customer_id or self.customer_id,
            "last_message": scope.last_message,
            "selected_product": (
                selected.product_id if selected is not None and hasattr(selected, "product_id") else None
            ),
            "available_products": [
                product.product_id if hasattr(product, "product_id") else product
                for product in scope.last_products
            ],
        }


if __name__ == "__main__":
    print("=" * 80)
    print("AGENT MEMORY TEST")
    print("=" * 80)

    memory = AgentMemory(default_ttl_seconds=600)
    print(
        memory.set_session_value(
            session_id="sess_12345",
            customer_id=5176,
            key="pending_offer",
            value={"product_id": 101, "price": 1839.08},
            ttl_seconds=600,
        )
    )
    print(memory.get_session_value(session_id="sess_12345", customer_id=5176, key="pending_offer"))
    print("=" * 80)
