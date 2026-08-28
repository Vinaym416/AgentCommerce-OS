"""
AGENTCOMMERCE OS
PHASE 05 — CUSTOMER-AWARE COMMERCE AGENT

Flow:

Customer
   ↓
Application provides customer_id
   ↓
Customer Context
   ↓
Buyer Agent
   ↓
Product Retriever
   ↓
Opportunity Engine
   ↓
Merchant Decision Engine
   ↓
Policy Engine
   ↓
Safe Commerce Decision

The Commerce Agent does NOT directly execute payments.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORTS
# ============================================================

from script.agents.buyer_agent import BuyerAgent
from script.agents.schemas import ProductCandidate
from script.agents.negotiation_agent import NegotiationAgent
from script.agents.checkout_agent import CheckoutAgent
from script.agents.payment_agent import PaymentAgent, PaymentResult
from script.agents.order_agent import OrderAgent, OrderResult

from script.transaction.transaction_manager import TransactionManager
from script.transaction.transaction_state import TransactionState

from script.catalog.product_retriever import ProductRetriever

from script.context.customer_context import CustomerContext
from script.context.opportunity_engine import OpportunityEngine
from script.context.agent_memory import AgentMemory

from script.policy.merchant_decision_engine import (
    MerchantDecisionEngine
)

from script.policy.policy_engine import (
    PolicyEngine
)


# ============================================================
# COMMERCE AGENT
# ============================================================

class CommerceAgent:

    def __init__(self):

        print(
            "Initializing AgentCommerce OS..."
        )

        self.buyer_agent = BuyerAgent()

        self.product_retriever = ProductRetriever()

        self.customer_context = CustomerContext()

        self.opportunity_engine = OpportunityEngine()

        self.merchant_engine = MerchantDecisionEngine()

        self.negotiation_agent = NegotiationAgent()

        self.checkout_agent = CheckoutAgent()

        self.payment_agent = PaymentAgent()

        self.order_agent = OrderAgent()

        self.transaction_manager = TransactionManager()

        self.policy_engine = PolicyEngine()

        self.memory = AgentMemory()

        print(
            "All agent tools initialized."
        )

    def process_payment(
        self,
        product_id: int,
        amount: float,
        payment_method: str = "UPI",
        simulate_failure: bool = False,
    ):
        """Execute payment explicitly after checkout approval."""
        return self.payment_agent.process_payment(
            product_id=product_id,
            amount=amount,
            payment_method=payment_method,
            simulate_failure=simulate_failure,
        )

    # ========================================================
    # MAIN PROCESS
    # ========================================================

    def process(
        self,
        message: str,
        customer_id: Optional[int] = None,
        payment_method: str = "UPI",
        execute_payment: bool = False,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:

        if not message or not message.strip():
            raise ValueError(
                "Customer message cannot be empty."
            )

        trace: List[str] = []

        self.memory.set_message(message)

        if customer_id is not None:
            self.memory.set_customer(customer_id)

        transaction = (
            self.transaction_manager.get(customer_id)
            if customer_id is not None
            else None
        )

        pending_offer = self.memory.get_pending_offer()

        if (
            pending_offer is not None
            and
            transaction is not None
            and self._is_acceptance_message(message)
            and transaction.status in {
                TransactionState.OFFER_CREATED,
                TransactionState.COUNTER_OFFERED,
            }
        ):
            return self._complete_transaction(
                transaction=transaction,
                payment_method=payment_method,
                execute_payment=execute_payment,
                simulate_failure=simulate_failure,
            )

        # ----------------------------------------------------
        # 1. CUSTOMER CONTEXT
        # ----------------------------------------------------

        trace.append(
            "CUSTOMER_CONTEXT"
        )

        customer = (
            self.customer_context.get_customer(
                customer_id
            )
        )

        # ----------------------------------------------------
        # 2. BUYER AGENT
        # ----------------------------------------------------

        trace.append(
            "BUYER_AGENT"
        )

        intent = (
            self.buyer_agent.analyze(
                message
            )
        )

        self.memory.set_intent(intent)

        # ----------------------------------------------------
        # 3. PRODUCT RETRIEVAL
        # ----------------------------------------------------

        trace.append(
            "PRODUCT_RETRIEVER"
        )

        referenced_product = (
            self.memory.resolve_product_reference(
                message
            )
        )

        if referenced_product:
            trace.append("AGENT_MEMORY")
            products = [referenced_product]

        else:
            product_rows = (
                self.product_retriever.search(
                    budget=intent.budget,
                    limit=5
                )
            )

            products = self._rows_to_products(
                product_rows
            )

            self.memory.set_products(products)

        # ----------------------------------------------------
        # NO PRODUCTS
        # ----------------------------------------------------

        if not products:

            trace.append(
                "NO_PRODUCT_MATCH"
            )

            return self._build_response(
                intent=intent,
                customer=customer,
                products=[],
                merchant_decision=None,
                negotiation=None,
                checkout=None,
                payment=None,
                order=None,
                policy_result=None,
                final_action="NO_PRODUCT_MATCH",
                trace=trace,
                purchase_score=0.0,
                discount_score=0.0
            )

        # ----------------------------------------------------
        # 4. TOP PRODUCT
        # ----------------------------------------------------

        top_product = products[0]

        # ----------------------------------------------------
        # 5. CUSTOMER + PRODUCT INTELLIGENCE
        # ----------------------------------------------------

        trace.append(
            "OPPORTUNITY_ENGINE"
        )

        intelligence = (
            self.opportunity_engine.calculate(
                intent=intent,
                product=top_product,
                customer=customer
            )
        )

        purchase_score = (
            intelligence[
                "purchase_opportunity_score"
            ]
        )

        discount_score = (
            intelligence[
                "discount_opportunity_score"
            ]
        )

        # ----------------------------------------------------
        # 6. MERCHANT DECISION
        # ----------------------------------------------------

        trace.append(
            "MERCHANT_DECISION_ENGINE"
        )

        merchant_decision = (
            self.merchant_engine.decide(

                product_id=(
                    top_product.product_id
                ),

                purchase_opportunity_score=(
                    purchase_score
                ),

                discount_opportunity_score=(
                    discount_score
                ),

                product_price=(
                    top_product.current_price
                )
            )
        )

        self.memory.set_merchant_decision(merchant_decision)

        # ----------------------------------------------------
        # 7. NEGOTIATION AGENT
        # ----------------------------------------------------

        customer_requested_discount = (
            intent.discount_requested
            and
            intent.max_discount_requested
            is not None
        )

        trace.append(
            "NEGOTIATION_AGENT"
        )

        negotiation = self.negotiation_agent.negotiate(
            requested_discount=(
                intent.max_discount_requested
                if customer_requested_discount
                else None
            ),
            merchant_max_discount=(
                merchant_decision.approved_discount_percent
            ),
            purchase_opportunity_score=purchase_score,
            discount_opportunity_score=discount_score
        )

        self.memory.set_negotiation_result(negotiation)

        # ----------------------------------------------------
        # 8. DETERMINE WHETHER DISCOUNT ACTION IS NEEDED
        # ----------------------------------------------------

        merchant_proposed_discount = (
            merchant_decision
            .approved_discount_percent
            > 0
        )

        discount_action_required = (
            customer_requested_discount
            or
            merchant_proposed_discount
        )

        # ----------------------------------------------------
        # 8A. NORMAL PRODUCT RECOMMENDATION
        # ----------------------------------------------------

        if not discount_action_required:

            trace.append(
                "NO_DISCOUNT_ACTION"
            )

            final_action = (
                self._recommendation_action(
                    merchant_decision
                )
            )

            trace.append(
                "FINAL_DECISION"
            )

            checkout = None

            payment = None

            order = None

            return self._build_response(
                intent=intent,
                customer=customer,
                products=products,
                merchant_decision=(
                    merchant_decision
                ),
                negotiation=negotiation,
                checkout=checkout,
                payment=payment,
                order=order,
                policy_result=None,
                final_action=final_action,
                trace=trace,
                purchase_score=purchase_score,
                discount_score=discount_score
            )

        # ----------------------------------------------------
        # 9B. DISCOUNT / OFFER ACTION
        # ----------------------------------------------------

        trace.append(
            "POLICY_ENGINE"
        )

        requested_discount = negotiation.offered_discount

        policy_result = (
            self.policy_engine.evaluate_discount(

                product_price=(
                    top_product.current_price
                ),

                requested_discount_percent=(
                    requested_discount
                ),

                purchase_opportunity_score=(
                    purchase_score
                )
            )
        )

        self.memory.set_policy_result(policy_result)

        # ----------------------------------------------------
        # 9. FINAL ACTION
        # ----------------------------------------------------

        trace.append(
            "FINAL_DECISION"
        )

        final_action = (
            self._commercial_action(
                intent=intent,
                merchant_decision=(
                    merchant_decision
                ),
                negotiation=negotiation,
                policy_result=(
                    policy_result
                )
            )
        )

        # ----------------------------------------------------
        # 10. CHECKOUT
        # ----------------------------------------------------

        checkout = None
        payment = None
        order = None

        if final_action in {"OFFER_REQUESTED", "COUNTER_OFFER"}:
            transaction_status = (
                TransactionState.COUNTER_OFFERED
                if final_action == "COUNTER_OFFER"
                else TransactionState.OFFER_CREATED
            )

            self._save_transaction(
                customer_id=customer_id,
                product_id=top_product.product_id,
                original_price=top_product.current_price,
                discount_percent=policy_result.get(
                    "approved_discount_percent",
                    0,
                ),
                final_price=policy_result.get(
                    "final_price",
                    top_product.current_price,
                ),
                status=transaction_status,
            )

            self.memory.set_pending_offer({
                "product_id": top_product.product_id,
                "original_price": top_product.current_price,
                "discount_percent": policy_result.get(
                    "approved_discount_percent",
                    0,
                ),
                "final_price": policy_result.get(
                    "final_price",
                    top_product.current_price,
                ),
            })

        payment = self._execute_payment(
            checkout=checkout,
            payment_method=payment_method,
            simulate_failure=simulate_failure,
           execute_payment=execute_payment,
        )

        order = self._create_order(
            customer_id=customer_id,
            payment=payment,
        )

        # ----------------------------------------------------
        # 11. FINAL RESPONSE
        # ----------------------------------------------------

        return self._build_response(
            intent=intent,
            customer=customer,
            products=products,
            merchant_decision=(
                merchant_decision
            ),
            negotiation=negotiation,
            checkout=checkout,
            payment=payment,
            order=order,
            policy_result=(
                policy_result
            ),
            final_action=final_action,
            trace=trace,
            purchase_score=purchase_score,
            discount_score=discount_score
        )

    def _execute_payment(
        self,
        checkout,
        payment_method: str,
        execute_payment: bool,
        simulate_failure: bool = False,
    ) -> Optional[PaymentResult]:
        if not execute_payment or checkout is None:
            return None

        if not checkout.payment_ready:
            return None

        return self.process_payment(
            product_id=checkout.product_id,
            amount=checkout.final_price,
            payment_method=payment_method,
            simulate_failure=simulate_failure,
        )

    def _is_acceptance_message(self, message: str) -> bool:
        text = " ".join(message.lower().strip().split())
        acceptance_phrases = {
            "yes",
            "accept",
            "okay",
            "ok",
            "yes i'll take it",
            "yes, i'll take it",
            "i'll take it",
            "ill take it",
            "take it",
            "i accept",
            "accepted",
            "deal",
            "sounds good",
            "go ahead",
            "buy it",
            "i'll buy it",
            "purchase",
            "proceed",
            "proceed with it",
        }
        return any(phrase in text for phrase in acceptance_phrases)

    def _save_transaction(
        self,
        customer_id: Optional[int],
        product_id: int,
        original_price: float,
        discount_percent: float,
        final_price: float,
        status: str,
    ) -> Optional[TransactionState]:
        if customer_id is None:
            return None

        return self.transaction_manager.create_or_update(
            customer_id=customer_id,
            product_id=product_id,
            original_price=round(float(original_price), 2),
            discount_percent=round(float(discount_percent), 2),
            final_price=round(float(final_price), 2),
            status=status,
            checkout_ready=False,
            payment_status="NOT_STARTED",
            payment_transaction_id=None,
            order_id=None,
            customer_accepted=False,
        )

    def _complete_transaction(
        self,
        transaction: TransactionState,
        payment_method: str,
        execute_payment: bool,
        simulate_failure: bool,
    ) -> Dict[str, Any]:
        transaction.customer_accepted = True
        transaction.status = TransactionState.OFFER_ACCEPTED

        checkout = self.checkout_agent.prepare_checkout(
            product_id=transaction.product_id,
            product_price=transaction.original_price,
            discount_percent=transaction.discount_percent,
        )
        transaction.checkout_ready = checkout.payment_ready
        transaction.status = (
            TransactionState.CHECKOUT_READY
            if checkout.payment_ready
            else TransactionState.ORDER_FAILED
        )

        if execute_payment and checkout.payment_ready:
            transaction.status = TransactionState.PAYMENT_PENDING

        payment = self._execute_payment(
            checkout=checkout,
            payment_method=payment_method,
            execute_payment=execute_payment,
            simulate_failure=simulate_failure,
        )

        if payment is None:
            transaction.payment_status = "NOT_STARTED"
        else:
            transaction.payment_status = payment.status
            transaction.payment_transaction_id = payment.transaction_id

            transaction.status = (
                TransactionState.PAYMENT_SUCCESS
                if payment.status == "PAYMENT_SUCCESS"
                else TransactionState.PAYMENT_FAILED
            )

        order = self._create_order(
            customer_id=transaction.customer_id,
            payment=payment,
        )

        if order is not None:
            transaction.status = TransactionState.ORDER_CREATED
            transaction.order_id = order.order_id
        elif payment is not None and payment.status == "PAYMENT_SUCCESS":
            transaction.status = TransactionState.ORDER_FAILED

        self.memory.clear_pending_offer()

        return self._build_transaction_response(
            transaction=transaction,
            checkout=checkout,
            payment=payment,
            order=order,
        )

    def _build_transaction_response(
        self,
        transaction: TransactionState,
        checkout,
        payment: Optional[PaymentResult],
        order: Optional[OrderResult],
    ) -> Dict[str, Any]:
        final_action = (
            "ORDER_CREATED"
            if order is not None
            else "PAYMENT_FAILED"
            if payment is not None
            and payment.status != "PAYMENT_SUCCESS"
            else "CUSTOMER_ACCEPTED"
        )

        result: Dict[str, Any] = {
            "customer": {
                "customer_id": transaction.customer_id,
                "known_customer": True,
            },
            "transaction": {
                "status": transaction.status,
                "customer_accepted": transaction.customer_accepted,
                "product_id": transaction.product_id,
                "discount_percent": transaction.discount_percent,
                "final_price": transaction.final_price,
            },
            "final_action": final_action,
            "checkout": None,
            "payment": None,
            "order": None,
        }

        if checkout:
            result["checkout"] = {
                "status": checkout.status,
                "product_id": checkout.product_id,
                "original_price": checkout.original_price,
                "discount_percent": checkout.discount_percent,
                "discount_amount": checkout.discount_amount,
                "final_price": checkout.final_price,
                "currency": checkout.currency,
                "payment_ready": checkout.payment_ready,
                "reason": checkout.reason,
            }

        if payment:
            result["payment"] = {
                "status": payment.status,
                "product_id": payment.product_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "transaction_id": payment.transaction_id,
                "reason": payment.reason,
            }

        if order:
            result["order"] = {
                "status": order.status,
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "product_id": order.product_id,
                "amount": order.amount,
                "currency": order.currency,
                "payment_transaction_id": order.payment_transaction_id,
                "created_at": order.created_at,
                "reason": order.reason,
            }

        return result

    def _create_order(
        self,
        customer_id: Optional[int],
        payment: Optional[PaymentResult],
    ) -> Optional[OrderResult]:
        if payment is None or payment.status != "PAYMENT_SUCCESS":
            return None

        return self.order_agent.create_order(
            customer_id=customer_id,
            product_id=payment.product_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_status="SUCCESS",
            payment_transaction_id=payment.transaction_id,
        )

    # ========================================================
    # PRODUCT CONVERSION
    # ========================================================

    def _rows_to_products(
        self,
        product_rows
    ) -> List[ProductCandidate]:

        products: List[ProductCandidate] = []

        if product_rows is None:
            return products

        if len(product_rows) == 0:
            return products

        for _, row in product_rows.iterrows():

            products.append(
                ProductCandidate(

                    product_id=int(
                        row["product_id"]
                    ),

                    category_name=str(
                        row["category_name"]
                    ),

                    current_price=float(
                        row["current_price"]
                    ),

                    conversion_rate=float(
                        row["conversion_rate"]
                    ),

                    demand_score=float(
                        row["demand_score"]
                    ),

                    quality_score=float(
                        row["quality_score"]
                    ),

                    product_score=float(
                        row["product_score"]
                    ),

                    rating=float(
                        row["avg_rating"]
                    )
                )
            )

        return products

    # ========================================================
    # NORMAL RECOMMENDATION
    # ========================================================

    def _recommendation_action(
        self,
        merchant_decision
    ) -> str:

        if merchant_decision is None:
            return "RECOMMEND_PRODUCT"

        # These actions refer to discount/commercial strategy.
        # They do NOT mean the product itself is rejected.

        return "RECOMMEND_PRODUCT"

    # ========================================================
    # DISCOUNT COMMERCIAL ACTION
    # ========================================================

    def _commercial_action(
        self,
        intent,
        merchant_decision,
        negotiation,
        policy_result
    ) -> str:

        if policy_result is None:
            return "RECOMMEND_PRODUCT"

        allowed = policy_result.get(
            "allowed",
            False
        )

        approved_discount = float(
            policy_result.get(
                "approved_discount_percent",
                0
            )
        )

        # ----------------------------------------------------
        # DISCOUNT NOT ALLOWED
        # ----------------------------------------------------

        if not allowed:

            if intent.discount_requested:
                return "COUNTER_OFFER"

            return "RECOMMEND_PRODUCT"

        # ----------------------------------------------------
        # DISCOUNT APPROVED
        # ----------------------------------------------------

        if approved_discount > 0:

            if negotiation.counter_offer:
                return "COUNTER_OFFER"

            if (
                merchant_decision
                and
                merchant_decision.merchant_action
                == "NEGOTIATE"
            ):
                return "NEGOTIATE"

            return "OFFER_REQUESTED"

        return "RECOMMEND_PRODUCT"

    # ========================================================
    # RESPONSE
    # ========================================================

    def _build_response(
        self,
        intent,
        customer,
        products,
        merchant_decision,
        negotiation,
        checkout,
        payment,
        order,
        policy_result,
        final_action,
        trace,
        purchase_score,
        discount_score
    ) -> Dict[str, Any]:

        result = {

            "customer": {
                "customer_id": (
                    customer["customer_id"]
                    if customer
                    else None
                ),

                "known_customer": (
                    customer is not None
                )
            },

            "customer_context": (
                self._customer_summary(
                    customer
                )
                if customer
                else None
            ),

            "customer_intent": {

                "intent": intent.intent,

                "budget": intent.budget,

                "urgency": intent.urgency,

                "discount_requested": (
                    intent.discount_requested
                ),

                "max_discount_requested": (
                    intent.max_discount_requested
                ),

                "product_preferences": (
                    intent.product_preferences
                ),

                "constraints": (
                    intent.constraints
                ),

                "confidence": intent.confidence
            },

            "intelligence": {

                "purchase_opportunity_score": (
                    purchase_score
                ),

                "discount_opportunity_score": (
                    discount_score
                )
            },

            "products": [],

            "merchant_decision": None,

            "negotiation": None,

            "checkout": None,

            "payment": None,

            "order": None,

            "policy": None,

            "final_action": final_action,

            "agent_trace": trace
        }

        # ----------------------------------------------------
        # PRODUCTS
        # ----------------------------------------------------

        for product in products:

            result["products"].append({

                "product_id": (
                    product.product_id
                ),

                "category": (
                    product.category_name
                ),

                "price": round(
                    product.current_price,
                    2
                ),

                "rating": round(
                    product.rating,
                    2
                ),

                "conversion_rate": round(
                    product.conversion_rate,
                    4
                ),

                "demand_score": round(
                    product.demand_score,
                    4
                ),

                "quality_score": round(
                    product.quality_score,
                    4
                ),

                "product_score": round(
                    product.product_score,
                    4
                )
            })

        # ----------------------------------------------------
        # MERCHANT DECISION
        # ----------------------------------------------------

        if merchant_decision:

            result["merchant_decision"] = {

                "action": (
                    merchant_decision
                    .merchant_action
                ),

                "approved_discount": (
                    merchant_decision
                    .approved_discount_percent
                ),

                "negotiation_allowed": (
                    merchant_decision
                    .negotiation_allowed
                ),

                "approval_status": (
                    merchant_decision
                    .approval_status
                )
            }

        if negotiation:

            result["negotiation"] = {
                "action": negotiation.action,
                "requested_discount": negotiation.requested_discount,
                "offered_discount": negotiation.offered_discount,
                "counter_offer": negotiation.counter_offer,
                "customer_accepted": (
                    final_action == "LIMITED_OFFER"
                ),
                "reason": negotiation.reason,
            }

        if checkout:
            result["checkout"] = {
                "status": checkout.status,
                "product_id": checkout.product_id,
                "original_price": checkout.original_price,
                "discount_percent": checkout.discount_percent,
                "discount_amount": checkout.discount_amount,
                "final_price": checkout.final_price,
                "currency": checkout.currency,
                "payment_ready": checkout.payment_ready,
                "reason": checkout.reason,
            }

        if payment:
            result["payment"] = {
                "status": payment.status,
                "product_id": payment.product_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "transaction_id": payment.transaction_id,
                "reason": payment.reason,
            }

        if order:
            result["order"] = {
                "status": order.status,
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "product_id": order.product_id,
                "amount": order.amount,
                "currency": order.currency,
                "payment_transaction_id": (
                    order.payment_transaction_id
                ),
                "created_at": order.created_at,
                "reason": order.reason,
            }

        # ----------------------------------------------------
        # POLICY
        # ----------------------------------------------------

        if policy_result:

            result["policy"] = {

                "allowed": (
                    policy_result.get(
                        "allowed",
                        False
                    )
                ),

                "approved_discount": (
                    policy_result.get(
                        "approved_discount_percent",
                        0
                    )
                ),

                "discount_amount": (
                    policy_result.get(
                        "discount_amount",
                        0
                    )
                ),

                "final_price": (
                    policy_result.get(
                        "final_price",
                        products[0].current_price
                        if products
                        else 0
                    )
                ),

                "reasons": (
                    policy_result.get(
                        "reasons",
                        [
                            policy_result.get(
                                "reason",
                                ""
                            )
                        ]
                    )
                )
            }

        return result

    # ========================================================
    # CUSTOMER SUMMARY
    # ========================================================

    def _customer_summary(
        self,
        customer
    ) -> Dict[str, Any]:

        return {

            "sessions": (
                customer["sessions"]
            ),

            "purchases": (
                customer["purchases"]
            ),

            "purchase_rate": round(
                customer["purchase_rate"],
                4
            ),

            "average_order_value": round(
                customer["average_order_value"],
                2
            ),

            "average_discount": round(
                customer["average_discount"],
                2
            ),

            "cart_rate": round(
                customer["cart_rate"],
                4
            ),

            "abandonment_rate": round(
                customer["abandonment_rate"],
                4
            ),

            "customer_affinity_score": round(
                customer[
                    "customer_affinity_score"
                ],
                4
            ),

            "customer_buying_confidence": round(
                customer[
                    "customer_buying_confidence"
                ],
                4
            ),

            "discount_dependence_score": round(
                customer[
                    "discount_dependence_score"
                ],
                4
            ),

            "preferred_category": (
                customer[
                    "preferred_category"
                ]
            )
        }


# ============================================================
# CLI TEST
# ============================================================

def main():

    print("=" * 80)

    print(
        "AGENTCOMMERCE OS — CUSTOMER-AWARE COMMERCE AGENT"
    )

    print("=" * 80)

    try:

        agent = CommerceAgent()

    except Exception as exc:

        print(
            f"\nINITIALIZATION ERROR: "
            f"{type(exc).__name__}: {exc}"
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # Use a real customer from the dataset.
    # 5176 was inspected in the previous step.
    # --------------------------------------------------------

    customer_id = 5176

    test_queries = [

        "I want a product under ₹2000.",

        "I like this product but can you give me 10% off?",

        "Yes, I'll take it.",

        "Give me 50% discount and I'll buy immediately.",

        "Yes, I'll take the 10% counter offer."
    ]

    for query in test_queries:

        print("\n")
        print("=" * 80)
        print("CUSTOMER")
        print("=" * 80)

        print(
            f"Customer ID: {customer_id}"
        )

        print(
            f"Message: {query}"
        )

        try:

            result = agent.process(
                message=query,
                customer_id=customer_id, 
                payment_method="UPI",
                execute_payment=True
            )

            print("\n")
            print("=" * 80)
            print("AGENT RESULT")
            print("=" * 80)

            print(
                json.dumps(
                    result,
                    indent=4,
                    ensure_ascii=False
                )
            )

        except Exception as exc:

            print(
                f"\nPROCESSING ERROR: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":

    main()