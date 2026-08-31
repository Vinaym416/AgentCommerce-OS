"""
AGENTCOMMERCE OS
PHASE 05 — AGENT SESSION MEMORY (CUSTOMER-SCOPED)

Stores short-term conversational state for the Commerce Agent.

Purpose:
- Remember the customer
- Remember the last recommended products
- Remember the selected product
- Resolve references such as:
    "this product"
    "that one"
    "the first one"
    "give me 10% off"

CRITICAL: Memory is CUSTOMER-SCOPED, not global.
Each customer gets their own conversation context.

This is SHORT-TERM agent memory per customer.
It is not the long-term customer intelligence system.
"""


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


class AgentMemory:
    """Customer-scoped conversation memory manager."""

    def __init__(self):
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

    def _get_scope(self, customer_id=None):
        if customer_id is None:
            return self
        if customer_id not in self.scopes:
            self.scopes[customer_id] = CustomerMemoryScope()
        return self.scopes[customer_id]

    def set_customer(self, customer_id):
        self.customer_id = customer_id

    def set_message(self, message, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_message = message
        if customer_id is None:
            self.last_message = message

    def get_message(self, customer_id=None):
        return self._get_scope(customer_id).last_message

    def set_intent(self, intent, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_intent = intent
        if customer_id is None:
            self.last_intent = intent

    def get_intent(self, customer_id=None):
        return self._get_scope(customer_id).last_intent

    def set_products(self, products, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_products = products
        if products:
            scope.selected_product = products[0]
        if customer_id is None:
            self.last_products = products
            self.selected_product = products[0] if products else None

    def get_products(self, customer_id=None):
        return self._get_scope(customer_id).last_products

    def select_product(self, index=0, customer_id=None):
        scope = self._get_scope(customer_id)

        if not scope.last_products:
            return None
        if index < 0 or index >= len(scope.last_products):
            return None

        scope.selected_product = scope.last_products[index]
        if customer_id is None:
            self.selected_product = scope.selected_product
        return scope.selected_product

    def get_selected_product(self, customer_id=None):
        return self._get_scope(customer_id).selected_product

    def set_merchant_decision(self, decision, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_merchant_decision = decision
        if customer_id is None:
            self.last_merchant_decision = decision

    def get_merchant_decision(self, customer_id=None):
        return self._get_scope(customer_id).last_merchant_decision

    def set_negotiation_result(self, result, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_negotiation_result = result
        if customer_id is None:
            self.last_negotiation_result = result

    def get_negotiation_result(self, customer_id=None):
        return self._get_scope(customer_id).last_negotiation_result

    def set_policy_result(self, result, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.last_policy_result = result
        if customer_id is None:
            self.last_policy_result = result

    def get_policy_result(self, customer_id=None):
        return self._get_scope(customer_id).last_policy_result

    def set_pending_offer(self, offer, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.pending_offer = offer
        if customer_id is None:
            self.pending_offer = offer

    def get_pending_offer(self, customer_id=None):
        return self._get_scope(customer_id).pending_offer

    def clear_pending_offer(self, customer_id=None):
        scope = self._get_scope(customer_id)
        scope.pending_offer = None
        if customer_id is None:
            self.pending_offer = None

    def resolve_product_reference(self, message, customer_id=None):
        """Resolve simple conversational references for a customer."""
        scope = self._get_scope(customer_id)
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

    def reset_product_selection(self, customer_id=None):
        """Clear the last product selection for a fresh search."""
        scope = self._get_scope(customer_id)
        scope.last_products = []
        scope.selected_product = None
        if customer_id is None:
            self.last_products = []
            self.selected_product = None

    def snapshot(self, customer_id=None):
        scope = self._get_scope(customer_id)
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

    memory = AgentMemory()
    memory.set_customer(5176)
    print("\nCustomer:")
    print(memory.customer_id)
    print("\nMemory initialized successfully.")
    print("\nSnapshot:")
    print(memory.snapshot(5176))
    print("=" * 80)
