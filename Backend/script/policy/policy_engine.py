"""Deterministic financial policy engine."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from script.database.repositories.product_repository import ProductRepository
from script.policy.policy_models import (
    MerchantPolicy,
    ProductEconomics,
    OfferProposal,
    PolicyResult,
    PolicyDecision,
    PolicyReasonCode,
)


BASE_DIR = Path(__file__).resolve().parents[2]
POLICY_PATH = BASE_DIR / "data" / "policies" / "merchant_policy.json"


class PolicyEngine:

    def __init__(self, policy_path=POLICY_PATH, policy=None):
        self.policy_path = Path(policy_path)
        if policy is not None:
            self.policy = policy
        else:
            with open(self.policy_path, "r", encoding="utf-8") as file:
                self.policy = json.load(file)
        self.merchant_policy = self._build_merchant_policy(self.policy)

    def _build_merchant_policy(self, source) -> MerchantPolicy:
        if isinstance(source, MerchantPolicy):
            return source

        discount = source.get("discount_policy", {})
        negotiation = source.get("negotiation_policy", {})
        approval = source.get("approval_policy", {})
        return MerchantPolicy(
            max_discount_percent=discount.get("max_discount_percent", 10.0),
            min_margin_percent=discount.get(
                "minimum_margin_percent",
                10.0,
            ),
            max_order_value=approval.get("max_order_value"),
            max_negotiation_rounds=negotiation.get("max_rounds", 2),
            requires_customer_confirmation=source.get(
                "requires_customer_confirmation", True
            ),
            auto_approve_discount_percent=approval.get(
                "auto_approve_below", 5.0
            ),
            auto_approve_order_value=approval.get(
                "auto_approve_below", 5000.0
            ),
        )

    def evaluate(
        self,
        proposal: OfferProposal,
        product: ProductEconomics,
    ) -> PolicyResult:
        reasons: List[PolicyReasonCode] = []

        if proposal.requested_price <= 0 or product.list_price <= 0 or product.cost_price < 0:
            return self._deny(proposal, product, PolicyReasonCode.INVALID_PRICE, "Price information is invalid.")

        if not product.inventory_available:
            return self._deny(proposal, product, PolicyReasonCode.PRODUCT_OUT_OF_STOCK, "Product is currently out of stock.")

        if proposal.negotiation_round > self.merchant_policy.max_negotiation_rounds:
            return self._deny(proposal, product, PolicyReasonCode.NEGOTIATION_LIMIT_EXCEEDED, "Maximum negotiation rounds exceeded.")

        discount_percent = ((product.list_price - proposal.requested_price) / product.list_price) * 100
        margin_amount = proposal.requested_price - product.cost_price
        minimum_margin = product.list_price * self.merchant_policy.min_margin_percent / 100

        if (
            self.merchant_policy.max_order_value is not None
            and proposal.requested_price > self.merchant_policy.max_order_value
        ):
            reasons.append(PolicyReasonCode.MAX_ORDER_VALUE_EXCEEDED)
        if discount_percent > self.merchant_policy.max_discount_percent:
            reasons.append(PolicyReasonCode.DISCOUNT_LIMIT_EXCEEDED)
        if margin_amount < minimum_margin:
            reasons.append(PolicyReasonCode.MINIMUM_MARGIN_VIOLATED)

        if not reasons:
            return self._allow(proposal, product, discount_percent, margin_amount)

        max_discount_price = product.list_price * (1 - self.merchant_policy.max_discount_percent / 100)
        minimum_margin_price = product.cost_price + minimum_margin
        safe_price = max(max_discount_price, minimum_margin_price)

        if (
            safe_price <= product.list_price
            and (
                self.merchant_policy.max_order_value is None
                or safe_price <= self.merchant_policy.max_order_value
            )
        ):
            modified_discount = ((product.list_price - safe_price) / product.list_price) * 100
            return PolicyResult(
                decision=PolicyDecision.MODIFY,
                original_price=product.list_price,
                requested_price=proposal.requested_price,
                approved_price=round(safe_price, 2),
                discount_percent=round(modified_discount, 2),
                margin_amount=round(safe_price - product.cost_price, 2),
                reason_codes=reasons,
                message="Requested offer was modified to the maximum safe price.",
                evidence={"product_id": product.product_id, "approved_price": round(safe_price, 2)},
            )

        return PolicyResult(
            decision=PolicyDecision.ESCALATE,
            original_price=product.list_price,
            requested_price=proposal.requested_price,
            approved_price=None,
            discount_percent=round(discount_percent, 2),
            margin_amount=round(margin_amount, 2),
            reason_codes=reasons,
            requires_human_approval=True,
            message="Human approval is required.",
            evidence={"product_id": product.product_id},
        )

    def _allow(self, proposal, product, discount_percent, margin_amount):
        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            original_price=product.list_price,
            requested_price=proposal.requested_price,
            approved_price=round(proposal.requested_price, 2),
            discount_percent=round(discount_percent, 2),
            margin_amount=round(margin_amount, 2),
            requires_human_approval=self.merchant_policy.requires_customer_confirmation,
            message="Offer satisfies merchant policy.",
            evidence={"product_id": product.product_id},
        )

    def _deny(self, proposal, product, reason, message):
        return PolicyResult(
            decision=PolicyDecision.DENY,
            original_price=product.list_price,
            requested_price=proposal.requested_price,
            approved_price=None,
            discount_percent=0.0,
            margin_amount=proposal.requested_price - product.cost_price,
            reason_codes=[reason],
            message=message,
            evidence={"product_id": product.product_id},
        )

    def evaluate_policy(
        self,
        customer_id: Optional[int] = None,
        product_id: Optional[int] = None,
        requested_discount: Optional[float] = None,
        approved_discount: Optional[float] = None,
        purchase_score: float = 0.0,
        product_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Final gatekeeper for offer approval. Returns the agent-facing policy contract."""
        discount_policy = self.policy.get("discount_policy", {})
        max_discount = float(discount_policy.get("max_discount_percent", 20.0))
        requires_high_intent = bool(discount_policy.get("discount_requires_high_intent", False))

        if product_price is None and product_id is not None:
            product_row = ProductRepository().get_by_product_id(int(product_id))
            if product_row is not None:
                product_price = float(product_row.get("current_price") or product_row.get("price") or 0.0)

        product_price = float(product_price or 0.0)
        requested_discount = max(float(requested_discount or 0.0), 0.0)
        approved_discount = float(approved_discount if approved_discount is not None else requested_discount)

        violations: List[str] = []

        if product_price <= 0:
            return {
                "is_allowed": False,
                "final_discount_percent": 0.0,
                "final_price": 0.0,
                "policy_violations": ["INVALID_PRODUCT_PRICE"],
                "requires_approval": True,
            }

        if approved_discount > max_discount:
            approved_discount = max_discount
            violations.append("EXCEEDS_MAX_LIMIT")

        if requires_high_intent and float(purchase_score or 0.0) < 0.60:
            violations.append("LOW_PURCHASE_INTENT")

        is_allowed = not violations
        final_discount_percent = round(max(0.0, approved_discount), 2)
        final_price = round(product_price * (1 - (final_discount_percent / 100.0)), 2)
        requires_approval = (
            bool(violations)
            or final_discount_percent > float(self.merchant_policy.auto_approve_discount_percent)
        )

        return {
            "is_allowed": is_allowed,
            "final_discount_percent": final_discount_percent,
            "final_price": final_price,
            "policy_violations": violations,
            "requires_approval": requires_approval,
        }

    def evaluate_discount(self, product_price, requested_discount_percent, purchase_opportunity_score):
        discount_policy = self.policy["discount_policy"]
        product_price = float(product_price or 0.0)
        requested_discount_percent = float(requested_discount_percent or 0.0)
        purchase_opportunity_score = float(purchase_opportunity_score or 0.0)

        if not discount_policy["enabled"]:
            return {"allowed": False, "approved_discount_percent": 0, "reason": "discount_disabled"}

        max_discount = float(discount_policy["max_discount_percent"])
        if discount_policy["discount_requires_high_intent"] and purchase_opportunity_score < 0.60:
            return {"allowed": False, "approved_discount_percent": 0, "reason": "insufficient_purchase_intent"}

        approved = min(max(requested_discount_percent, 0.0), max_discount)
        discount_amount = product_price * approved / 100
        reasons = [
            "requested_discount_exceeds_policy_limit"
            if requested_discount_percent > max_discount
            else "discount_within_merchant_policy"
        ]
        return {
            "allowed": True,
            "approved_discount_percent": round(approved, 2),
            "discount_amount": round(discount_amount, 2),
            "final_price": round(product_price - discount_amount, 2),
            "reasons": reasons,
        }

    def evaluate_negotiation(self, order_value, requested_discount_percent, negotiation_round):
        policy = self.policy["negotiation_policy"]
        if not policy["enabled"]:
            return {"allowed": False, "reason": "negotiation_disabled"}
        if order_value < policy["minimum_order_value"]:
            return {"allowed": False, "reason": "order_value_below_negotiation_threshold"}
        if negotiation_round >= policy["max_rounds"]:
            return {"allowed": False, "reason": "maximum_negotiation_rounds_reached"}
        if requested_discount_percent > self.merchant_policy.max_discount_percent:
            return {"allowed": False, "reason": "requested_discount_exceeds_discount_policy"}
        return {"allowed": True, "reason": "negotiation_allowed"}

    def evaluate_order_approval(self, order_value):
        policy = self.policy["approval_policy"]
        if order_value < policy["auto_approve_below"]:
            return {"status": "AUTO_APPROVED", "reason": "below_auto_approval_threshold"}
        if order_value >= policy["require_approval_above"]:
            return {"status": "HUMAN_APPROVAL_REQUIRED", "reason": "order_exceeds_approval_threshold"}
        return {"status": "STANDARD_APPROVAL", "reason": "order_within_standard_threshold"}

    def can_agent_execute(self, permission):
        return self.policy.get("agent_permissions", {}).get(permission, False)
