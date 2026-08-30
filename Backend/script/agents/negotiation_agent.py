"""
AGENTCOMMERCE OS
PHASE 06 — NEGOTIATION AGENT

OWNERSHIP: Price Negotiation Only
────────────────────────────────

The Negotiation Agent handles ONLY:

    original_price
           ↓
    customer context
           ↓
    merchant policy
           ↓
    negotiated_price

What it does NOT do:
    ❌ Verify payments
    ❌ Process Razorpay
    ❌ Create orders
    ❌ Access frontend payment data
    ❌ Modify transaction outside negotiation

Result:
    - action: ACCEPT_OFFER | COUNTER_OFFER | NO_NEGOTIATION
    - offered_discount: The merchant's response to customer request
    
This result is consumed by:
    - CommerceAgent (for response building)
    - NegotiationAgent → TransactionManager (price update)
    
The negotiated_price + discount_percent → final_price
is calculated by TransactionManager, not NegotiationAgent.
"""

from dataclasses import dataclass
from typing import Optional


# ============================================================
# NEGOTIATION RESULT
# ============================================================

@dataclass
class NegotiationResult:

    action: str

    requested_discount: float

    offered_discount: float

    counter_offer: bool

    reason: str


# ============================================================
# NEGOTIATION AGENT
# ============================================================

class NegotiationAgent:

    def __init__(self):

        print("Negotiation Agent initialized.")

    # ========================================================
    # NEGOTIATE
    # ========================================================

    def negotiate(
        self,
        requested_discount: Optional[float],
        merchant_max_discount: float,
        purchase_opportunity_score: float,
        discount_opportunity_score: float,
    ) -> NegotiationResult:

        # ----------------------------------------------------
        # No discount requested
        # ----------------------------------------------------

        if requested_discount is None:

            return NegotiationResult(

                action="NO_NEGOTIATION",

                requested_discount=0.0,

                offered_discount=0.0,

                counter_offer=False,

                reason="customer_did_not_request_discount"
            )

        requested_discount = max(
            0.0,
            float(requested_discount)
        )

        merchant_max_discount = max(
            0.0,
            float(merchant_max_discount)
        )

        # ----------------------------------------------------
        # Customer request is within merchant limit
        # ----------------------------------------------------

        if requested_discount <= merchant_max_discount:

            return NegotiationResult(

                action="ACCEPT_OFFER",

                requested_discount=requested_discount,

                offered_discount=requested_discount,

                counter_offer=False,

                reason="requested_discount_within_merchant_limit"
            )

        # ----------------------------------------------------
        # Customer asks for more than merchant allows
        # ----------------------------------------------------

        counter_discount = merchant_max_discount

        # ----------------------------------------------------
        # Strong buying opportunity
        # ----------------------------------------------------

        if (
            purchase_opportunity_score >= 0.70
            and discount_opportunity_score >= 0.40
        ):

            return NegotiationResult(

                action="COUNTER_OFFER",

                requested_discount=requested_discount,

                offered_discount=counter_discount,

                counter_offer=True,

                reason="high_purchase_opportunity_counter_at_merchant_limit"
            )

        # ----------------------------------------------------
        # Normal opportunity
        # ----------------------------------------------------

        return NegotiationResult(

            action="COUNTER_OFFER",

            requested_discount=requested_discount,

            offered_discount=counter_discount,

            counter_offer=True,

            reason="requested_discount_exceeds_merchant_limit"
        )


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("AGENTCOMMERCE OS — NEGOTIATION AGENT")
    print("=" * 80)

    agent = NegotiationAgent()

    tests = [

        {
            "requested_discount": None,
            "merchant_max_discount": 10,
            "purchase_opportunity_score": 0.70,
            "discount_opportunity_score": 0.20,
        },

        {
            "requested_discount": 10,
            "merchant_max_discount": 10,
            "purchase_opportunity_score": 0.70,
            "discount_opportunity_score": 0.47,
        },

        {
            "requested_discount": 50,
            "merchant_max_discount": 10,
            "purchase_opportunity_score": 0.76,
            "discount_opportunity_score": 0.45,
        },

        {
            "requested_discount": 30,
            "merchant_max_discount": 10,
            "purchase_opportunity_score": 0.40,
            "discount_opportunity_score": 0.20,
        },
    ]

    for test in tests:

        result = agent.negotiate(**test)

        print("\n")
        print("-" * 80)
        print("TEST")
        print("-" * 80)

        print(result)        