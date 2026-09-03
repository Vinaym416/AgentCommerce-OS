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
from typing import Any, Dict, Optional


# ============================================================
# NEGOTIATION RESULT
# ============================================================

@dataclass
class NegotiationResult:

    action: str = "REJECT"

    requested_discount: float = 0.0

    offered_discount: float = 0.0

    counter_offer: bool = False

    reason: str = ""

    offer_value: float = 0.0

    message_template: str = ""

    expires_in_seconds: int = 300

    is_final_offer: bool = False

    conversation_turn: int = 0

    def __post_init__(self):
        self.requested_discount = float(self.requested_discount or 0.0)
        self.offered_discount = float(self.offered_discount or 0.0)
        self.offer_value = float(self.offer_value if self.offer_value is not None else self.offered_discount)
        self.expires_in_seconds = int(self.expires_in_seconds or 300)
        self.conversation_turn = int(self.conversation_turn or 0)

        if self.action not in {"ACCEPT", "REJECT", "COUNTER_OFFER"}:
            self.action = "REJECT"

        if self.message_template == "" and self.offer_value > 0:
            self.message_template = f"I can offer {self.offer_value}% off if you buy now."
        elif self.message_template == "":
            self.message_template = "I can't offer additional discount right now."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "offer_value": self.offer_value,
            "message_template": self.message_template,
            "expires_in_seconds": self.expires_in_seconds,
            "is_final_offer": self.is_final_offer,
        }


# ============================================================
# NEGOTIATION AGENT
# ============================================================

class NegotiationAgent:

    def __init__(self, max_counter_offers: int = 3):
        self.max_counter_offers = max(1, int(max_counter_offers))
        self.state = {"conversation_turn": 0}
        print("Negotiation Agent initialized.")

    # ========================================================
    # NEGOTIATE
    # ========================================================

    def negotiate(
        self,
        requested_discount: Optional[float] = None,
        merchant_max_discount: float = 0.0,
        purchase_opportunity_score: float = 0.0,
        discount_opportunity_score: float = 0.0,
        customer_request: Optional[float] = None,
        merchant_limit: Optional[float] = None,
        opportunity_scores: Optional[Dict[str, float]] = None,
        conversation_turn: int = 0,
        **kwargs,
    ) -> NegotiationResult:

        if customer_request is not None:
            requested_discount = customer_request
        if merchant_limit is not None:
            merchant_max_discount = merchant_limit

        if opportunity_scores:
            purchase_opportunity_score = float(
                opportunity_scores.get(
                    "purchase_opportunity_score",
                    opportunity_scores.get("purchase", purchase_opportunity_score),
                )
            )
            discount_opportunity_score = float(
                opportunity_scores.get(
                    "discount_opportunity_score",
                    opportunity_scores.get("discount", discount_opportunity_score),
                )
            )

        requested_discount = max(0.0, float(requested_discount or 0.0))
        merchant_max_discount = max(0.0, float(merchant_max_discount or 0.0))
        conversation_turn = int(conversation_turn or self.state.get("conversation_turn", 0))
        self.state["conversation_turn"] = conversation_turn

        if requested_discount <= 0:
            return NegotiationResult(
                action="REJECT",
                requested_discount=0.0,
                offered_discount=0.0,
                counter_offer=False,
                reason="customer_did_not_request_discount",
                offer_value=0.0,
                message_template="I can't offer additional discount right now.",
                expires_in_seconds=300,
                is_final_offer=True,
                conversation_turn=conversation_turn,
            )

        if conversation_turn >= self.max_counter_offers:
            return NegotiationResult(
                action="REJECT",
                requested_discount=requested_discount,
                offered_discount=0.0,
                counter_offer=False,
                reason="maximum_negotiation_rounds_reached",
                offer_value=0.0,
                message_template="I can't offer additional discount right now.",
                expires_in_seconds=300,
                is_final_offer=True,
                conversation_turn=conversation_turn,
            )

        if requested_discount <= merchant_max_discount:
            return NegotiationResult(
                action="ACCEPT",
                requested_discount=requested_discount,
                offered_discount=requested_discount,
                counter_offer=False,
                reason="requested_discount_within_merchant_limit",
                offer_value=requested_discount,
                message_template=f"I can offer {requested_discount}% off if you buy now.",
                expires_in_seconds=300,
                is_final_offer=False,
                conversation_turn=conversation_turn,
            )

        counter_discount = min(float(merchant_max_discount), float(requested_discount))
        is_high_opportunity = (
            purchase_opportunity_score >= 0.70
            and discount_opportunity_score >= 0.40
        )

        if is_high_opportunity:
            action = "COUNTER_OFFER"
            reason = "high_purchase_opportunity_counter_at_merchant_limit"
            is_final_offer = conversation_turn >= self.max_counter_offers - 1
        else:
            action = "COUNTER_OFFER"
            reason = "requested_discount_exceeds_merchant_limit"
            is_final_offer = conversation_turn >= self.max_counter_offers - 1

        return NegotiationResult(
            action=action,
            requested_discount=requested_discount,
            offered_discount=counter_discount,
            counter_offer=True,
            reason=reason,
            offer_value=counter_discount,
            message_template=f"I can offer {counter_discount}% off if you buy now.",
            expires_in_seconds=300,
            is_final_offer=is_final_offer,
            conversation_turn=conversation_turn,
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