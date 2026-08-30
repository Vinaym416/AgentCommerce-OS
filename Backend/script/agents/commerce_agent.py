# """
# AGENTCOMMERCE OS
# PHASE 05 — COMMERCE DECISION AGENT

# OWNERSHIP: Commerce Decisions Only
# ───────────────────────────────────

# CommerceAgent decides:

#     What should I sell?
#            ↓
#     At what offer?
#            ↓
#     Why?

# Flow:

# Customer Message
#    ↓
# BuyerAgent (intent analysis)
#    ↓
# ProductRetriever (what to sell)
#    ↓
# OpportunityEngine (why / opportunity score)
#    ↓
# MerchantDecisionEngine (what offer)
#    ↓
# NegotiationAgent (discount negotiation)
#    ↓
# CommerceExecutionAgent (ONLY for execution)

# What CommerceAgent does NOT do:
#     ❌ Process Razorpay payments
#     ❌ Create orders
#     ❌ Access payment verification
#     ❌ Know about webhooks
#     ❌ Verify payment signatures
    
# What CommerceExecutionAgent does:
#     ✅ Create Razorpay order
#     ✅ Handle payment verification
#     ✅ Receive payment webhooks
#     ✅ Create internal orders after webhook confirmation

# CRITICAL: CommerceAgent delegates ALL payment/order work
# to CommerceExecutionAgent. No direct payment handling.
# """

# import json
# import sys
# from pathlib import Path
# from typing import Any, Dict, List, Optional


# # ============================================================
# # PROJECT ROOT
# # ============================================================

# ROOT = Path(__file__).resolve().parents[2]

# if str(ROOT) not in sys.path:
#     sys.path.insert(0, str(ROOT))


# # ============================================================
# # IMPORTS
# # ============================================================

# from script.agents.buyer_agent import BuyerAgent
# from script.agents.schemas import ProductCandidate
# from script.agents.negotiation_agent import NegotiationAgent
# from script.agents.commerce_execution_agent import CommerceExecutionAgent
# from script.agents.payment_agent import PaymentResult
# from script.agents.order_agent import OrderResult

# from script.transaction.transaction_manager import TransactionManager
# from script.transaction.transaction_state import TransactionState

# from script.catalog.product_retriever import ProductRetriever

# from script.context.customer_context import CustomerContext
# from script.context.opportunity_engine import OpportunityEngine
# from script.context.agent_memory import AgentMemory

# from script.policy.merchant_decision_engine import (
#     MerchantDecisionEngine
# )

# from script.policy.policy_engine import (
#     PolicyEngine
# )


# # ============================================================
# # COMMERCE AGENT
# # ============================================================

# class CommerceAgent:

#     def __init__(self):

#         print(
#             "Initializing AgentCommerce OS..."
#         )

#         self.buyer_agent = BuyerAgent()

#         self.product_retriever = ProductRetriever()

#         self.customer_context = CustomerContext()

#         self.opportunity_engine = OpportunityEngine()

#         self.merchant_engine = MerchantDecisionEngine()

#         self.negotiation_agent = NegotiationAgent()

#         self.execution_agent = CommerceExecutionAgent()

#         self.transaction_manager = TransactionManager()

#         self.policy_engine = PolicyEngine()

#         self.memory = AgentMemory()

#         print(
#             "All agent tools initialized."
#         )

#     # ========================================================
#     # MAIN PROCESS
#     # ========================================================

#     def process(
#         self,
#         message: str,
#         customer_id: Optional[int] = None,
#         payment_method: str = "UPI",
#         execute_payment: bool = False,
#         simulate_failure: bool = False,
#     ) -> Dict[str, Any]:

#         if not message or not message.strip():
#             raise ValueError(
#                 "Customer message cannot be empty."
#             )

#         trace: List[str] = []

#         self.memory.set_message(message)

#         if customer_id is not None:
#             self.memory.set_customer(customer_id)

#         transaction = (
#             self.transaction_manager.get(customer_id)
#             if customer_id is not None
#             else None
#         )

#         pending_offer = self.memory.get_pending_offer()

#         if (
#             pending_offer is not None
#             and
#             transaction is not None
#             and self._is_acceptance_message(message)
#             and transaction.status in {
#                 TransactionState.OFFER_CREATED,
#                 TransactionState.COUNTER_OFFERED,
#             }
#         ):
#             return self._complete_transaction(
#                 transaction=transaction,
#                 payment_method=payment_method,
#                 execute_payment=execute_payment,
#                 simulate_failure=simulate_failure,
#             )

#         # ----------------------------------------------------
#         # 1. CUSTOMER CONTEXT
#         # ----------------------------------------------------

#         trace.append(
#             "CUSTOMER_CONTEXT"
#         )

#         customer = (
#             self.customer_context.get_customer(
#                 customer_id
#             )
#         )
#         customer = self.customer_context.get_customer(customer_id)

#         if customer is None:
#             trace.append("ANONYMOUS_CUSTOMER")

#         # ----------------------------------------------------
#         # 2. BUYER AGENT
#         # ----------------------------------------------------

#         trace.append(
#             "BUYER_AGENT"
#         )

#         intent = (
#             self.buyer_agent.analyze(
#                 message
#             )
#         )

#         self.memory.set_intent(intent)

#         # ----------------------------------------------------
#         # 3. PRODUCT RETRIEVAL
#         # ----------------------------------------------------

#         trace.append(
#             "PRODUCT_RETRIEVER"
#         )

#         referenced_product = (
#             self.memory.resolve_product_reference(
#                 message
#             )
#         )

#         if referenced_product:
#             trace.append("AGENT_MEMORY")
#             products = [referenced_product]

#         else:
#             product_rows = (
#                 self.product_retriever.search(
#                     budget=intent.budget,
#                     limit=5
#                 )
#             )

#             products = self._rows_to_products(
#                 product_rows
#             )

#             self.memory.set_products(products)

#         # ----------------------------------------------------
#         # NO PRODUCTS
#         # ----------------------------------------------------

#         if not products:

#             trace.append(
#                 "NO_PRODUCT_MATCH"
#             )

#             return self._build_response(
#                 intent=intent,
#                 customer=customer,
#                 products=[],
#                 merchant_decision=None,
#                 negotiation=None,
#                 checkout=None,
#                 payment=None,
#                 order=None,
#                 policy_result=None,
#                 final_action="NO_PRODUCT_MATCH",
#                 trace=trace,
#                 purchase_score=0.0,
#                 discount_score=0.0
#             )

#         # ----------------------------------------------------
#         # 4. TOP PRODUCT
#         # ----------------------------------------------------

#         top_product = products[0]

#         # ----------------------------------------------------
#         # 5. CUSTOMER + PRODUCT INTELLIGENCE
#         # ----------------------------------------------------

#         trace.append(
#             "OPPORTUNITY_ENGINE"
#         )

#         intelligence = (
#             self.opportunity_engine.calculate(
#                 intent=intent,
#                 product=top_product,
#                 customer=customer
#             )
#         )

#         purchase_score = (
#             intelligence[
#                 "purchase_opportunity_score"
#             ]
#         )

#         discount_score = (
#             intelligence[
#                 "discount_opportunity_score"
#             ]
#         )

#         # ----------------------------------------------------
#         # 6. MERCHANT DECISION
#         # ----------------------------------------------------

#         trace.append(
#             "MERCHANT_DECISION_ENGINE"
#         )

#         merchant_decision = (
#             self.merchant_engine.decide(

#                 product_id=(
#                     top_product.product_id
#                 ),

#                 purchase_opportunity_score=(
#                     purchase_score
#                 ),

#                 discount_opportunity_score=(
#                     discount_score
#                 ),

#                 product_price=(
#                     top_product.current_price
#                 )
#             )
#         )

#         self.memory.set_merchant_decision(merchant_decision)

#         # ----------------------------------------------------
#         # 7. NEGOTIATION AGENT
#         # ----------------------------------------------------

#         customer_requested_discount = (
#             intent.discount_requested
#             and
#             intent.max_discount_requested
#             is not None
#         )

#         trace.append(
#             "NEGOTIATION_AGENT"
#         )

#         negotiation = self.negotiation_agent.negotiate(
#             requested_discount=(
#                 intent.max_discount_requested
#                 if customer_requested_discount
#                 else None
#             ),
#             merchant_max_discount=(
#                 merchant_decision.approved_discount_percent
#             ),
#             purchase_opportunity_score=purchase_score,
#             discount_opportunity_score=discount_score
#         )

#         self.memory.set_negotiation_result(negotiation)

#         # ----------------------------------------------------
#         # 8. DETERMINE WHETHER DISCOUNT ACTION IS NEEDED
#         # ----------------------------------------------------

#         merchant_proposed_discount = (
#             merchant_decision
#             .approved_discount_percent
#             > 0
#         )

#         discount_action_required = (
#             customer_requested_discount
#             or
#             merchant_proposed_discount
#         )

#         # ----------------------------------------------------
#         # 8A. NORMAL PRODUCT RECOMMENDATION
#         # ----------------------------------------------------

#         if not discount_action_required:

#             trace.append(
#                 "NO_DISCOUNT_ACTION"
#             )

#             final_action = (
#                 self._recommendation_action(
#                     merchant_decision
#                 )
#             )

#             trace.append(
#                 "FINAL_DECISION"
#             )

#             checkout = None

#             payment = None

#             order = None

#             return self._build_response(
#                 intent=intent,
#                 customer=customer,
#                 products=products,
#                 merchant_decision=(
#                     merchant_decision
#                 ),
#                 negotiation=negotiation,
#                 checkout=checkout,
#                 payment=payment,
#                 order=order,
#                 policy_result=None,
#                 final_action=final_action,
#                 trace=trace,
#                 purchase_score=purchase_score,
#                 discount_score=discount_score
#             )

#         # ----------------------------------------------------
#         # 9B. DISCOUNT / OFFER ACTION
#         # ----------------------------------------------------

#         trace.append(
#             "POLICY_ENGINE"
#         )

#         requested_discount = negotiation.offered_discount

#         policy_result = (
#             self.policy_engine.evaluate_discount(

#                 product_price=(
#                     top_product.current_price
#                 ),

#                 requested_discount_percent=(
#                     requested_discount
#                 ),

#                 purchase_opportunity_score=(
#                     purchase_score
#                 )
#             )
#         )

#         self.memory.set_policy_result(policy_result)

#         # ----------------------------------------------------
#         # 9. FINAL ACTION
#         # ----------------------------------------------------

#         trace.append(
#             "FINAL_DECISION"
#         )

#         final_action = (
#             self._commercial_action(
#                 intent=intent,
#                 merchant_decision=(
#                     merchant_decision
#                 ),
#                 negotiation=negotiation,
#                 policy_result=(
#                     policy_result
#                 )
#             )
#         )

#         # ----------------------------------------------------
#         # 10. CHECKOUT
#         # ----------------------------------------------------

#         checkout = None
#         payment = None
#         order = None

#         if final_action in {"OFFER_REQUESTED", "COUNTER_OFFER"}:
#             transaction_status = (
#                 TransactionState.COUNTER_OFFERED
#                 if final_action == "COUNTER_OFFER"
#                 else TransactionState.OFFER_CREATED
#             )

#             self._save_transaction(
#                 customer_id=customer_id,
#                 product_id=top_product.product_id,
#                 original_price=top_product.current_price,
#                 discount_percent=policy_result.get(
#                     "approved_discount_percent",
#                     0,
#                 ),
#                 final_price=policy_result.get(
#                     "final_price",
#                     top_product.current_price,
#                 ),
#                 status=transaction_status,
#             )

#             self.memory.set_pending_offer({
#                 "product_id": top_product.product_id,
#                 "original_price": top_product.current_price,
#                 "discount_percent": policy_result.get(
#                     "approved_discount_percent",
#                     0,
#                 ),
#                 "final_price": policy_result.get(
#                     "final_price",
#                     top_product.current_price,
#                 ),
#             })

#         # ----------------------------------------------------
#         # 11. DELEGATE EXECUTION TO COMMERCE EXECUTION AGENT
#         # ----------------------------------------------------

#         if final_action in {"OFFER_REQUESTED", "COUNTER_OFFER"}:
#             return self._build_response(
#                 intent=intent,
#                 customer=customer,
#                 products=products,
#                 merchant_decision=merchant_decision,
#                 negotiation=negotiation,
#                 checkout=None,
#                 payment=None,
#                 order=None,
#                 policy_result=policy_result,
#                 final_action=final_action,
#                 trace=trace,
#                 purchase_score=purchase_score,
#                 discount_score=discount_score,
#             )

#         if final_action in {"RECOMMEND_PRODUCT", "NEGOTIATE"}:
#             return self._build_response(
#                 intent=intent,
#                 customer=customer,
#                 products=products,
#                 merchant_decision=merchant_decision,
#                 negotiation=negotiation,
#                 checkout=None,
#                 payment=None,
#                 order=None,
#                 policy_result=policy_result,
#                 final_action=final_action,
#                 trace=trace,
#                 purchase_score=purchase_score,
#                 discount_score=discount_score,
#             )

#         return self._build_response(
#             intent=intent,
#             customer=customer,
#             products=products,
#             merchant_decision=merchant_decision,
#             negotiation=negotiation,
#             checkout=None,
#             payment=None,
#             order=None,
#             policy_result=policy_result,
#             final_action=final_action,
#             trace=trace,
#             purchase_score=purchase_score,
#             discount_score=discount_score,
#         )

#     def _execute_payment(
#         self,
#         checkout,
#         payment_method: str,
#         execute_payment: bool,
#         simulate_failure: bool = False,
#     ) -> Optional[PaymentResult]:
#         """
#         DEPRECATED: Payment execution is now handled exclusively
#         by CommerceExecutionAgent.
        
#         CommerceAgent does NOT process payments directly.
#         Payment flows through CommerceExecutionAgent.execute()
#         which handles Razorpay checkout and verification.
#         """
#         return None

#     def _is_acceptance_message(self, message: str) -> bool:
#         text = " ".join(message.lower().strip().split())
#         acceptance_phrases = {
#             "yes",
#             "accept",
#             "okay",
#             "ok",
#             "yes i'll take it",
#             "yes, i'll take it",
#             "i'll take it",
#             "ill take it",
#             "take it",
#             "i accept",
#             "accepted",
#             "deal",
#             "sounds good",
#             "go ahead",
#             "buy it",
#             "i'll buy it",
#             "purchase",
#             "proceed",
#             "proceed with it",
#         }
#         return any(phrase in text for phrase in acceptance_phrases)

#     def _save_transaction(
#         self,
#         customer_id: Optional[int],
#         product_id: int,
#         original_price: float,
#         discount_percent: float,
#         final_price: float,
#         status: str,
#     ) -> Optional[TransactionState]:
#         if customer_id is None:
#             return None

#         return self.transaction_manager.create_or_update(
#             customer_id=customer_id,
#             product_id=product_id,
#             original_price=round(float(original_price), 2),
#             discount_percent=round(float(discount_percent), 2),
#             final_price=round(float(final_price), 2),
#             status=status,
#             checkout_ready=False,
#             payment_status="NOT_STARTED",
#             payment_transaction_id=None,
#             order_id=None,
#             customer_accepted=False,
#         )

#     def _complete_transaction(
#         self,
#         transaction: TransactionState,
#         payment_method: str,
#         execute_payment: bool,
#         simulate_failure: bool,
#     ) -> Dict[str, Any]:
#         transaction.customer_accepted = True
#         transaction.status = TransactionState.OFFER_ACCEPTED

#         execution_result = self.execution_agent.execute(
#             customer_id=transaction.customer_id,
#             product_id=transaction.product_id,
#             product_price=transaction.original_price,
#             discount_percent=transaction.discount_percent,
#             payment_method=payment_method,
#             execute_payment=execute_payment,
#             simulate_failure=simulate_failure,
#         )

#         self.memory.clear_pending_offer()

#         response = {
#             "customer": {
#                 "customer_id": transaction.customer_id,
#                 "known_customer": True,
#             },
#             "transaction": {
#                 "status": transaction.status,
#                 "customer_accepted": transaction.customer_accepted,
#                 "product_id": transaction.product_id,
#                 "discount_percent": transaction.discount_percent,
#                 "final_price": transaction.final_price,
#             },
#             "final_action": execution_result.get("final_action", "EXECUTION_COMPLETE"),
#             "checkout": execution_result.get("checkout"),
#             "payment": execution_result.get("payment"),
#             "order": execution_result.get("order"),
#             "agent_trace": execution_result.get("agent_trace", []),
#         }

#         if execution_result.get("order") is not None:
#             transaction.status = TransactionState.ORDER_CREATED
#             transaction.order_id = execution_result["order"].get("order_id")
#         elif execution_result.get("payment") is not None and execution_result["payment"].get("status") == "PAYMENT_SUCCESS":
#             transaction.status = TransactionState.ORDER_FAILED

#         return response

#     def _build_transaction_response(
#         self,
#         transaction: TransactionState,
#         checkout,
#         payment: Optional[PaymentResult],
#         order: Optional[OrderResult],
#     ) -> Dict[str, Any]:
#         final_action = (
#             "ORDER_CREATED"
#             if order is not None
#             else "PAYMENT_FAILED"
#             if payment is not None
#             and payment.status != "PAYMENT_SUCCESS"
#             else "CUSTOMER_ACCEPTED"
#         )

#         result: Dict[str, Any] = {
#             "customer": {
#                 "customer_id": transaction.customer_id,
#                 "known_customer": True,
#             },
#             "transaction": {
#                 "status": transaction.status,
#                 "customer_accepted": transaction.customer_accepted,
#                 "product_id": transaction.product_id,
#                 "discount_percent": transaction.discount_percent,
#                 "final_price": transaction.final_price,
#             },
#             "final_action": final_action,
#             "checkout": None,
#             "payment": None,
#             "order": None,
#         }

#         if checkout:
#             result["checkout"] = {
#                 "status": checkout.status,
#                 "product_id": checkout.product_id,
#                 "original_price": checkout.original_price,
#                 "discount_percent": checkout.discount_percent,
#                 "discount_amount": checkout.discount_amount,
#                 "final_price": checkout.final_price,
#                 "currency": checkout.currency,
#                 "payment_ready": checkout.payment_ready,
#                 "reason": checkout.reason,
#             }

#         if payment:
#             result["payment"] = {
#                 "status": payment.status,
#                 "product_id": payment.product_id,
#                 "amount": payment.amount,
#                 "currency": payment.currency,
#                 "payment_method": payment.payment_method,
#                 "transaction_id": payment.transaction_id,
#                 "reason": payment.reason,
#             }

#         if order:
#             result["order"] = {
#                 "status": order.status,
#                 "order_id": order.order_id,
#                 "customer_id": order.customer_id,
#                 "product_id": order.product_id,
#                 "amount": order.amount,
#                 "currency": order.currency,
#                 "payment_transaction_id": order.payment_transaction_id,
#                 "created_at": order.created_at,
#                 "reason": order.reason,
#             }

#         return result

#     def _create_order(
#         self,
#         customer_id: Optional[int],
#         payment: Optional[PaymentResult],
#     ) -> Optional[OrderResult]:
#         """
#         DEPRECATED: Order creation is now handled exclusively
#         by CommerceExecutionAgent and OrderAgent.
        
#         CommerceAgent does NOT create orders directly.
#         Order creation is triggered by successful payment
#         webhooks from Razorpay, processed asynchronously.
#         """
#         return None

#     # ========================================================
#     # PRODUCT CONVERSION
#     # ========================================================

#     def _rows_to_products(
#         self,
#         product_rows
#     ) -> List[ProductCandidate]:

#         products: List[ProductCandidate] = []

#         if product_rows is None:
#             return products

#         if len(product_rows) == 0:
#             return products

#         for _, row in product_rows.iterrows():

#             products.append(
#                 ProductCandidate(

#                     product_id=int(
#                         row["product_id"]
#                     ),

#                     category_name=str(
#                         row["category_name"]
#                     ),

#                     current_price=float(
#                         row["current_price"]
#                     ),

#                     conversion_rate=float(
#                         row["conversion_rate"]
#                     ),

#                     demand_score=float(
#                         row["demand_score"]
#                     ),

#                     quality_score=float(
#                         row["quality_score"]
#                     ),

#                     product_score=float(
#                         row["product_score"]
#                     ),

#                     rating=float(
#                         row["avg_rating"]
#                     )
#                 )
#             )

#         return products

#     # ========================================================
#     # NORMAL RECOMMENDATION
#     # ========================================================

#     def _recommendation_action(
#         self,
#         merchant_decision
#     ) -> str:

#         if merchant_decision is None:
#             return "RECOMMEND_PRODUCT"

#         # These actions refer to discount/commercial strategy.
#         # They do NOT mean the product itself is rejected.

#         return "RECOMMEND_PRODUCT"

#     # ========================================================
#     # DISCOUNT COMMERCIAL ACTION
#     # ========================================================

#     def _commercial_action(
#         self,
#         intent,
#         merchant_decision,
#         negotiation,
#         policy_result
#     ) -> str:

#         if policy_result is None:
#             return "RECOMMEND_PRODUCT"

#         allowed = policy_result.get(
#             "allowed",
#             False
#         )

#         approved_discount = float(
#             policy_result.get(
#                 "approved_discount_percent",
#                 0
#             )
#         )

#         # ----------------------------------------------------
#         # DISCOUNT NOT ALLOWED
#         # ----------------------------------------------------

#         if not allowed:

#             if intent.discount_requested:
#                 return "COUNTER_OFFER"

#             return "RECOMMEND_PRODUCT"

#         # ----------------------------------------------------
#         # DISCOUNT APPROVED
#         # ----------------------------------------------------

#         if approved_discount > 0:

#             if negotiation.counter_offer:
#                 return "COUNTER_OFFER"

#             if (
#                 merchant_decision
#                 and
#                 merchant_decision.merchant_action
#                 == "NEGOTIATE"
#             ):
#                 return "NEGOTIATE"

#             return "OFFER_REQUESTED"

#         return "RECOMMEND_PRODUCT"

#     # ========================================================
#     # RESPONSE
#     # ========================================================

#     def _build_response(
#         self,
#         intent,
#         customer,
#         products,
#         merchant_decision,
#         negotiation,
#         checkout,
#         payment,
#         order,
#         policy_result,
#         final_action,
#         trace,
#         purchase_score,
#         discount_score
#     ) -> Dict[str, Any]:

#         result = {

#             "customer": {
#                 "customer_id": (
#                     customer["customer_id"]
#                     if customer
#                     else None
#                 ),

#                 "known_customer": (
#                     customer is not None
#                 )
#             },

#             "customer_context": (
#                 self._customer_summary(
#                     customer
#                 )
#                 if customer
#                 else None
#             ),

#             "customer_intent": {

#                 "intent": intent.intent,

#                 "budget": intent.budget,

#                 "urgency": intent.urgency,

#                 "discount_requested": (
#                     intent.discount_requested
#                 ),

#                 "max_discount_requested": (
#                     intent.max_discount_requested
#                 ),

#                 "product_preferences": (
#                     intent.product_preferences
#                 ),

#                 "constraints": (
#                     intent.constraints
#                 ),

#                 "confidence": intent.confidence
#             },

#             "intelligence": {

#                 "purchase_opportunity_score": (
#                     purchase_score
#                 ),

#                 "discount_opportunity_score": (
#                     discount_score
#                 )
#             },

#             "products": [],

#             "merchant_decision": None,

#             "negotiation": None,

#             "checkout": None,

#             "payment": None,

#             "order": None,

#             "policy": None,

#             "final_action": final_action,

#             "agent_trace": trace
#         }

#         # ----------------------------------------------------
#         # PRODUCTS
#         # ----------------------------------------------------

#         for product in products:

#             result["products"].append({

#                 "product_id": (
#                     product.product_id
#                 ),

#                 "category": (
#                     product.category_name
#                 ),

#                 "price": round(
#                     product.current_price,
#                     2
#                 ),

#                 "rating": round(
#                     product.rating,
#                     2
#                 ),

#                 "conversion_rate": round(
#                     product.conversion_rate,
#                     4
#                 ),

#                 "demand_score": round(
#                     product.demand_score,
#                     4
#                 ),

#                 "quality_score": round(
#                     product.quality_score,
#                     4
#                 ),

#                 "product_score": round(
#                     product.product_score,
#                     4
#                 )
#             })

#         # ----------------------------------------------------
#         # MERCHANT DECISION
#         # ----------------------------------------------------

#         if merchant_decision:

#             result["merchant_decision"] = {

#                 "action": (
#                     merchant_decision
#                     .merchant_action
#                 ),

#                 "approved_discount": (
#                     merchant_decision
#                     .approved_discount_percent
#                 ),

#                 "negotiation_allowed": (
#                     merchant_decision
#                     .negotiation_allowed
#                 ),

#                 "approval_status": (
#                     merchant_decision
#                     .approval_status
#                 )
#             }

#         if negotiation:

#             result["negotiation"] = {
#                 "action": negotiation.action,
#                 "requested_discount": negotiation.requested_discount,
#                 "offered_discount": negotiation.offered_discount,
#                 "counter_offer": negotiation.counter_offer,
#                 "customer_accepted": (
#                     final_action == "LIMITED_OFFER"
#                 ),
#                 "reason": negotiation.reason,
#             }

#         if checkout:
#             result["checkout"] = {
#                 "status": checkout.status,
#                 "product_id": checkout.product_id,
#                 "original_price": checkout.original_price,
#                 "discount_percent": checkout.discount_percent,
#                 "discount_amount": checkout.discount_amount,
#                 "final_price": checkout.final_price,
#                 "currency": checkout.currency,
#                 "payment_ready": checkout.payment_ready,
#                 "reason": checkout.reason,
#             }

#         if payment:
#             result["payment"] = {
#                 "status": payment.status,
#                 "product_id": payment.product_id,
#                 "amount": payment.amount,
#                 "currency": payment.currency,
#                 "payment_method": payment.payment_method,
#                 "transaction_id": payment.transaction_id,
#                 "reason": payment.reason,
#             }

#         if order:
#             result["order"] = {
#                 "status": order.status,
#                 "order_id": order.order_id,
#                 "customer_id": order.customer_id,
#                 "product_id": order.product_id,
#                 "amount": order.amount,
#                 "currency": order.currency,
#                 "payment_transaction_id": (
#                     order.payment_transaction_id
#                 ),
#                 "created_at": order.created_at,
#                 "reason": order.reason,
#             }

#         # ----------------------------------------------------
#         # POLICY
#         # ----------------------------------------------------

#         if policy_result:

#             result["policy"] = {

#                 "allowed": (
#                     policy_result.get(
#                         "allowed",
#                         False
#                     )
#                 ),

#                 "approved_discount": (
#                     policy_result.get(
#                         "approved_discount_percent",
#                         0
#                     )
#                 ),

#                 "discount_amount": (
#                     policy_result.get(
#                         "discount_amount",
#                         0
#                     )
#                 ),

#                 "final_price": (
#                     policy_result.get(
#                         "final_price",
#                         products[0].current_price
#                         if products
#                         else 0
#                     )
#                 ),

#                 "reasons": (
#                     policy_result.get(
#                         "reasons",
#                         [
#                             policy_result.get(
#                                 "reason",
#                                 ""
#                             )
#                         ]
#                     )
#                 )
#             }

#         return result

#     # ========================================================
#     # CUSTOMER SUMMARY
#     # ========================================================

#     def _customer_summary(
#         self,
#         customer
#     ) -> Dict[str, Any]:

#         return {

#             "sessions": (
#                 customer["sessions"]
#             ),

#             "purchases": (
#                 customer["purchases"]
#             ),

#             "purchase_rate": round(
#                 customer["purchase_rate"],
#                 4
#             ),

#             "average_order_value": round(
#                 customer["average_order_value"],
#                 2
#             ),

#             "average_discount": round(
#                 customer["average_discount"],
#                 2
#             ),

#             "cart_rate": round(
#                 customer["cart_rate"],
#                 4
#             ),

#             "abandonment_rate": round(
#                 customer["abandonment_rate"],
#                 4
#             ),

#             "customer_affinity_score": round(
#                 customer[
#                     "customer_affinity_score"
#                 ],
#                 4
#             ),

#             "customer_buying_confidence": round(
#                 customer[
#                     "customer_buying_confidence"
#                 ],
#                 4
#             ),

#             "discount_dependence_score": round(
#                 customer[
#                     "discount_dependence_score"
#                 ],
#                 4
#             ),

#             "preferred_category": (
#                 customer[
#                     "preferred_category"
#                 ]
#             )
#         }


# # ============================================================
# # CLI TEST
# # ============================================================

# def main():

#     print("=" * 80)

#     print(
#         "AGENTCOMMERCE OS — CUSTOMER-AWARE COMMERCE AGENT"
#     )

#     print("=" * 80)

#     try:

#         agent = CommerceAgent()

#     except Exception as exc:

#         print(
#             f"\nINITIALIZATION ERROR: "
#             f"{type(exc).__name__}: {exc}"
#         )

#         raise SystemExit(1)

#     # --------------------------------------------------------
#     # Use a real customer from the dataset.
#     # 5176 was inspected in the previous step.
#     # --------------------------------------------------------

#     customer_id = 5176

#     test_queries = [

#         "I want a product under ₹2000.",

#         "I like this product but can you give me 10% off?",

#         "Yes, I'll take it.",

#         "Give me 50% discount and I'll buy immediately.",

#         "Yes, I'll take the 10% counter offer."
#     ]

#     for query in test_queries:

#         print("\n")
#         print("=" * 80)
#         print("CUSTOMER")
#         print("=" * 80)

#         print(
#             f"Customer ID: {customer_id}"
#         )

#         print(
#             f"Message: {query}"
#         )

#         try:

#             result = agent.process(
#                 message=query,
#                 customer_id=customer_id, 
#                 payment_method="UPI",
#                 execute_payment=True
#             )

#             print("\n")
#             print("=" * 80)
#             print("AGENT RESULT")
#             print("=" * 80)

#             print(
#                 json.dumps(
#                     result,
#                     indent=4,
#                     ensure_ascii=False
#                 )
#             )

#         except Exception as exc:

#             print(
#                 f"\nPROCESSING ERROR: "
#                 f"{type(exc).__name__}: {exc}"
#             )


# if __name__ == "__main__":

#     main()




"""
AGENTCOMMERCE OS
PHASE 05 — COMMERCE DECISION AGENT

OWNERSHIP: Commerce Decisions Only
───────────────────────────────────

CommerceAgent decides:

    What should I sell?
           ↓
    At what offer?
           ↓
    Why?

Flow:

Customer Message
   ↓
BuyerAgent (intent analysis)
   ↓
ProductRetriever (what to sell)
   ↓
OpportunityEngine (why / opportunity score)
   ↓
MerchantDecisionEngine (what offer)
   ↓
NegotiationAgent (discount negotiation)
   ↓
CommerceExecutionAgent (ONLY for execution)

What CommerceAgent does NOT do:
    ❌ Process Razorpay payments
    ❌ Create orders
    ❌ Access payment verification
    ❌ Know about webhooks
    ❌ Verify payment signatures
    
What CommerceExecutionAgent does:
    ✅ Create Razorpay order
    ✅ Handle payment verification
    ✅ Receive payment webhooks
    ✅ Create internal orders after webhook confirmation

CRITICAL: CommerceAgent delegates ALL payment/order work
to CommerceExecutionAgent. No direct payment handling.
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
from script.agents.commerce_execution_agent import CommerceExecutionAgent
from script.agents.order_agent import OrderResult

# Compatibility alias for legacy type references kept by earlier test code.
# Real payment execution is handled by CommerceExecutionAgent and Razorpay services.
PaymentResult = Any

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

        self.execution_agent = CommerceExecutionAgent()

        self.transaction_manager = TransactionManager()

        self.policy_engine = PolicyEngine()

        self.memory = AgentMemory()

        print(
            "All agent tools initialized."
        )

    # ========================================================
    # MAIN PROCESS
    # ========================================================

    def process(
        self,
        message: str,
        customer_id: Optional[int] = None,
        product_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
        payment_method: str = "UPI",
        execute_payment: bool = False,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:

        if not message or not message.strip():
            raise ValueError(
                "Customer message cannot be empty."
            )

        trace: List[str] = []

        if customer_id is not None:
            self.memory.set_message(message, customer_id)

        transaction = None
        if transaction_id:
            transaction = self.transaction_manager.get_by_transaction_id(transaction_id)
        if transaction is None and customer_id is not None:
            transaction = self.transaction_manager.get(customer_id)

        pending_offer = (
            self.memory.get_pending_offer(customer_id)
            if customer_id is not None
            else None
        )

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
        customer = self.customer_context.get_customer(customer_id)

        if customer is None:
            trace.append("ANONYMOUS_CUSTOMER")

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

        if customer_id is not None:
            self.memory.set_intent(intent, customer_id)

        # ----------------------------------------------------
        # 3. PRODUCT RETRIEVAL
        # ----------------------------------------------------

        trace.append(
            "PRODUCT_RETRIEVER"
        )

        selected_product = (
            self.memory.get_selected_product(customer_id)
            if customer_id is not None
            else None
        )

        if product_id is not None and customer_id is not None:
            selected_product = next(
                (
                    product
                    for product in self.memory.get_products(customer_id)
                    if int(product.product_id) == int(product_id)
                ),
                selected_product,
            )
            if selected_product is not None:
                self.memory.select_product(
                    self.memory.get_products(customer_id).index(selected_product),
                    customer_id,
                )

        price_followup = (
            customer_id is not None
            and selected_product is not None
            and self._is_price_followup(message)
        )

        referenced_product = (
            self.memory.resolve_product_reference(message, customer_id)
            if customer_id is not None
            else None
        )

        if referenced_product or price_followup:
            trace.append("AGENT_MEMORY")
            products = [referenced_product or selected_product]

        else:
            product_rows = (
                self.product_retriever.search(
                    budget=intent.budget,
                    limit=None
                )
            )

            products = self._rows_to_products(
                product_rows
            )

            if customer_id is not None:
                self.memory.set_products(products, customer_id)

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

        if (
            selected_product is not None
            and (
                self._is_price_followup(message)
                or self._is_product_reference(message)
            )
        ):
            purchase_score = max(purchase_score, 0.72)
            if intent.discount_requested:
                discount_score = max(discount_score, 0.70)

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

        if customer_id is not None:
            self.memory.set_merchant_decision(merchant_decision, customer_id)

        # ----------------------------------------------------
        # 7. NEGOTIATION AGENT
        # ----------------------------------------------------

        customer_requested_discount = (
            bool(intent.discount_requested)
            or
            self._is_price_followup(message)
        )

        trace.append(
            "NEGOTIATION_AGENT"
        )

        negotiation = self.negotiation_agent.negotiate(
            requested_discount=(
                intent.max_discount_requested
                if customer_requested_discount and intent.max_discount_requested is not None
                else merchant_decision.approved_discount_percent
                if customer_requested_discount
                else None
            ),
            merchant_max_discount=(
                merchant_decision.approved_discount_percent
            ),
            purchase_opportunity_score=purchase_score,
            discount_opportunity_score=discount_score
        )

        if customer_id is not None:
            self.memory.set_negotiation_result(negotiation, customer_id)

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

            if customer_id is not None:
                self._save_transaction(
                    customer_id=customer_id,
                    product_id=top_product.product_id,
                    original_price=top_product.current_price,
                    discount_percent=0,
                    final_price=top_product.current_price,
                    status=TransactionState.OFFER_CREATED,
                )

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

        if customer_id is not None:
            self.memory.set_policy_result(policy_result, customer_id)

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

            transaction = self._save_transaction(
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

            if customer_id is not None:
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
                }, customer_id)

        # ----------------------------------------------------
        # 11. DELEGATE EXECUTION TO COMMERCE EXECUTION AGENT
        # ----------------------------------------------------

        if final_action in {"OFFER_REQUESTED", "COUNTER_OFFER"}:
            return self._build_response(
                intent=intent,
                customer=customer,
                products=products,
                merchant_decision=merchant_decision,
                negotiation=negotiation,
                checkout=None,
                payment=None,
                order=None,
                policy_result=policy_result,
                final_action=final_action,
                trace=trace,
                purchase_score=purchase_score,
                discount_score=discount_score,
            )

        if final_action in {"RECOMMEND_PRODUCT", "NEGOTIATE"}:
            return self._build_response(
                intent=intent,
                customer=customer,
                products=products,
                merchant_decision=merchant_decision,
                negotiation=negotiation,
                checkout=None,
                payment=None,
                order=None,
                policy_result=policy_result,
                final_action=final_action,
                trace=trace,
                purchase_score=purchase_score,
                discount_score=discount_score,
            )

        return self._build_response(
            intent=intent,
            customer=customer,
            products=products,
            merchant_decision=merchant_decision,
            negotiation=negotiation,
            checkout=None,
            payment=None,
            order=None,
            policy_result=policy_result,
            final_action=final_action,
            trace=trace,
            purchase_score=purchase_score,
            discount_score=discount_score,
        )

    def _execute_payment(
        self,
        checkout,
        payment_method: str,
        execute_payment: bool,
        simulate_failure: bool = False,
    ) -> Optional[PaymentResult]:
        """
        DEPRECATED: Payment execution is now handled exclusively
        by CommerceExecutionAgent.
        
        CommerceAgent does NOT process payments directly.
        Payment flows through CommerceExecutionAgent.execute()
        which handles Razorpay checkout and verification.
        """
        return None

    def _is_product_reference(self, message: str) -> bool:
        text = " ".join(message.lower().strip().split())
        return any(
            phrase in text
            for phrase in {
                "this product",
                "that product",
                "this one",
                "that one",
                "the product",
                "the item",
            }
        )

    def _is_price_followup(self, message: str) -> bool:
        text = " ".join(message.lower().strip().split())
        if not text:
            return False
        discount_phrases = {
            "discount",
            "off",
            "% off",
            "percent off",
            "cheaper",
            "price",
            "deal",
            "save",
            "reduce",
        }
        return (
            any(phrase in text for phrase in discount_phrases)
            or "%" in text
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
        transaction.status = TransactionState.CUSTOMER_ACCEPTED

        execution_result = self.execution_agent.execute(
            customer_id=transaction.customer_id,
            product_id=transaction.product_id,
            product_price=transaction.original_price,
            discount_percent=transaction.discount_percent,
            payment_method=payment_method,
            execute_payment=execute_payment,
            simulate_failure=simulate_failure,
        )

        self.memory.clear_pending_offer(transaction.customer_id)

        response = {
            "customer": {
                "customer_id": transaction.customer_id,
                "known_customer": True,
            },
            "transaction": {
                "transaction_id": transaction.transaction_id,
                "status": transaction.status,
                "customer_accepted": transaction.customer_accepted,
                "product_id": transaction.product_id,
                "discount_percent": transaction.discount_percent,
                "final_price": transaction.final_price,
            },
            "final_action": execution_result.get("final_action", "EXECUTION_COMPLETE"),
            "action": execution_result.get("final_action", "EXECUTION_COMPLETE"),
            "checkout": execution_result.get("checkout"),
            "payment": execution_result.get("payment"),
            "order": execution_result.get("order"),
            "agent_trace": execution_result.get("agent_trace", []),
        }

        if execution_result.get("order") is not None:
            transaction.status = TransactionState.ORDER_CREATED
            transaction.order_id = execution_result["order"].get("order_id")
            if execution_result["order"].get("status") == "CONFIRMED":
                transaction.status = TransactionState.COMPLETED
        elif execution_result.get("payment") is not None and execution_result["payment"].get("status") in {"PAYMENT_CAPTURED", "PAYMENT_SUCCESS"}:
            transaction.status = TransactionState.ORDER_FAILED

        return response

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
        """
        DEPRECATED: Order creation is now handled exclusively
        by CommerceExecutionAgent and OrderAgent.
        
        CommerceAgent does NOT create orders directly.
        Order creation is triggered by successful payment
        webhooks from Razorpay, processed asynchronously.
        """
        return None

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

                    product_name=str(
                        row.get("product_name", f"Product {int(row['product_id'])}")
                    ),

                    availability=str(
                        row.get("availability", "available")
                    ),

                    currency=str(
                        row.get("currency", "INR")
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

            "message": {
                "RECOMMEND_PRODUCT": "I found a few options for you.",
                "OFFER_REQUESTED": "I prepared an offer for this product.",
                "COUNTER_OFFER": "I checked the available offer and negotiated a better price for you.",
                "NEGOTIATE": "I'll check whether I can improve the price for you.",
                "PAYMENT_PENDING": "Great. Your checkout is ready.",
                "CHECKOUT_READY": "Great. Your checkout is ready.",
                "ORDER_CREATED": "Your payment was confirmed and your order was created.",
            }.get(final_action, "I've processed your request."),

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

            "offer": None,

            "transaction": None,

            "merchant_decision": None,

            "negotiation": None,

            "checkout": None,

            "payment": None,

            "order": None,

            "policy": None,

            "final_action": final_action,

            "action": final_action,

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

                "name": product.product_name,

                "category": (
                    product.category_name
                ),

                "availability": product.availability,

                "currency": product.currency,

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

        current_transaction = (
            self.transaction_manager.get(customer["customer_id"])
            if customer and customer.get("customer_id") is not None
            else None
        )

        if current_transaction:
            result["transaction"] = {
                "transaction_id": current_transaction.transaction_id,
                "status": current_transaction.status,
                "customer_id": current_transaction.customer_id,
                "product_id": current_transaction.product_id,
                "original_price": current_transaction.original_price,
                "discount_percent": current_transaction.discount_percent,
                "final_price": current_transaction.final_price,
            }

        if policy_result and products and final_action in {
            "OFFER_REQUESTED",
            "COUNTER_OFFER",
            "NEGOTIATE",
            "LIMITED_OFFER",
        }:
            result["offer"] = {
                "product_id": products[0].product_id,
                "name": products[0].product_name,
                "category": products[0].category_name,
                "original_price": round(products[0].current_price, 2),
                "discount_percent": policy_result.get(
                    "approved_discount_percent",
                    0,
                ),
                "discount_amount": policy_result.get(
                    "discount_amount",
                    0,
                ),
                "final_price": policy_result.get(
                    "final_price",
                    products[0].current_price,
                ),
                "currency": "INR",
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