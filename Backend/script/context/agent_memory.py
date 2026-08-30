"""
AGENTCOMMERCE OS
PHASE 05 — AGENT SESSION MEMORY

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

This is SHORT-TERM agent memory.
It is not the long-term customer intelligence system.
"""


class AgentMemory:

    def __init__(self):

        self.customer_id = None

        self.last_message = None

        self.last_intent = None

        self.last_products = []

        self.selected_product = None

        self.last_merchant_decision = None

        self.last_negotiation_result = None

        self.last_policy_result = None

        self.pending_offer = None


    # ============================================================
    # CUSTOMER
    # ============================================================

    def set_customer(self, customer_id):

        self.customer_id = customer_id


    # ============================================================
    # MESSAGE
    # ============================================================

    def set_message(self, message):

        self.last_message = message


    # ============================================================
    # INTENT
    # ============================================================

    def set_intent(self, intent):

        self.last_intent = intent


    # ============================================================
    # PRODUCTS
    # ============================================================

    def set_products(self, products):

        self.last_products = products

        # First product becomes the default selected product
        if products:

            self.selected_product = products[0]


    # ============================================================
    # SELECT PRODUCT
    # ============================================================

    def select_product(self, index=0):

        if not self.last_products:

            return None

        if index < 0 or index >= len(self.last_products):

            return None

        self.selected_product = self.last_products[index]

        return self.selected_product


    # ============================================================
    # GET SELECTED PRODUCT
    # ============================================================

    def get_selected_product(self):

        return self.selected_product


    # ============================================================
    # MERCHANT DECISION
    # ============================================================

    def set_merchant_decision(self, decision):

        self.last_merchant_decision = decision

    def set_negotiation_result(self, result):

        self.last_negotiation_result = result


    # ============================================================
    # POLICY
    # ============================================================

    def set_policy_result(self, result):

        self.last_policy_result = result

    def set_pending_offer(self, offer):

        self.pending_offer = offer

    def get_pending_offer(self):

        return self.pending_offer

    def clear_pending_offer(self):

        self.pending_offer = None


    # ============================================================
    # REFERENCE RESOLUTION
    # ============================================================

    def resolve_product_reference(self, message):

        """
        Resolve simple conversational references.

        Examples:

        "this product"
        "that product"
        "this one"
        "that one"

        -> currently selected product

        "first product"
        -> first recommendation

        "second product"
        -> second recommendation
        """

        text = message.lower().strip()

        # --------------------------------------------------------
        # Current product references
        # --------------------------------------------------------

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

                return self.selected_product


        # --------------------------------------------------------
        # Numbered product references
        # --------------------------------------------------------

        numbered_products = {

            "first product": 0,
            "second product": 1,
            "third product": 2,
            "fourth product": 3,
            "fifth product": 4,

        }


        for reference, index in numbered_products.items():

            if reference in text:

                return self.select_product(index)


        return None


    # ============================================================
    # MEMORY SNAPSHOT
    # ============================================================

    def snapshot(self):

        selected = self.selected_product

        return {

            "customer_id": self.customer_id,

            "last_message": self.last_message,

            "selected_product": (

                selected.product_id
                if selected
                else None
            ),

            "available_products": [

                product.product_id

                for product in self.last_products

            ],

        }


# ============================================================
# TEST
# ============================================================

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

    print(memory.snapshot())

    print("=" * 80)