from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ============================================================
# BUYER INTENT
# ============================================================

@dataclass
class BuyerIntent:
    intent: str

    budget: Optional[float] = None

    urgency: str = "normal"

    discount_requested: bool = False

    max_discount_requested: Optional[float] = None

    product_preferences: List[str] = field(default_factory=list)

    constraints: List[str] = field(default_factory=list)

    confidence: float = 0.0


# ============================================================
# PRODUCT
# ============================================================

@dataclass
class ProductCandidate:
    product_id: int

    category_name: str

    current_price: float

    conversion_rate: float

    demand_score: float

    quality_score: float

    product_score: float

    rating: float = 0.0


# ============================================================
# MERCHANT DECISION
# ============================================================

@dataclass
class MerchantDecision:

    merchant_action: str

    approved_discount_percent: float = 0.0

    negotiation_allowed: bool = False

    approval_status: str = "NOT_REQUIRED"

    reason: str = ""


# ============================================================
# POLICY RESULT
# ============================================================

@dataclass
class PolicyResult:

    allowed: bool

    approved_discount_percent: float = 0.0

    discount_amount: float = 0.0

    final_price: float = 0.0

    reasons: List[str] = field(default_factory=list)


# ============================================================
# AGENT RESPONSE
# ============================================================

@dataclass
class AgentResponse:

    intent: BuyerIntent

    products: List[ProductCandidate]

    merchant_decision: Optional[MerchantDecision]

    policy_result: Optional[PolicyResult]

    final_action: str

    message: str

    trace: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)