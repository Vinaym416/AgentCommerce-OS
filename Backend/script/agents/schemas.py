from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:  # pragma: no cover
    BaseModel = object
    ConfigDict = None
    Field = lambda *args, **kwargs: None


# ============================================================
# BUYER INTENT
# ============================================================

if ConfigDict is not None:
    class BuyerIntent(BaseModel):
        model_config = ConfigDict(extra="ignore", populate_by_name=True)

        intent: str = "PRODUCT_SEARCH"
        budget_min: Optional[float] = 0.0
        budget_max: Optional[float] = None
        currency: str = "INR"
        product_category: str = "general"
        discount_requested: bool = False
        discount_value: Optional[float] = None
        urgency: Literal["low", "medium", "high"] = "medium"
        confidence_score: float = 0.0

        product_preferences: List[str] = Field(default_factory=list)
        constraints: List[str] = Field(default_factory=list)

        @property
        def budget(self) -> Optional[float]:
            return self.budget_max

        @budget.setter
        def budget(self, value):
            self.budget_max = value

        @property
        def max_discount_requested(self) -> Optional[float]:
            return self.discount_value

        @max_discount_requested.setter
        def max_discount_requested(self, value):
            self.discount_value = value

        @property
        def confidence(self) -> float:
            return self.confidence_score

        @confidence.setter
        def confidence(self, value):
            self.confidence_score = value

        @property
        def urgency_level(self) -> str:
            return self.urgency

        def model_dump(self, *args, **kwargs):
            return super().model_dump(*args, **kwargs)

else:
    class BuyerIntent(BaseModel):
        intent: str = "PRODUCT_SEARCH"
        budget_min: Optional[float] = 0.0
        budget_max: Optional[float] = None
        currency: str = "INR"
        product_category: str = "general"
        discount_requested: bool = False
        discount_value: Optional[float] = None
        urgency: str = "medium"
        confidence_score: float = 0.0

        product_preferences: List[str] = []
        constraints: List[str] = []

        class Config:
            extra = "ignore"

        @property
        def budget(self) -> Optional[float]:
            return self.budget_max

        @budget.setter
        def budget(self, value):
            self.budget_max = value

        @property
        def max_discount_requested(self) -> Optional[float]:
            return self.discount_value

        @max_discount_requested.setter
        def max_discount_requested(self, value):
            self.discount_value = value

        @property
        def confidence(self) -> float:
            return self.confidence_score

        @confidence.setter
        def confidence(self, value):
            self.confidence_score = value

        def model_dump(self, *args, **kwargs):
            return self.__dict__.copy()


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

    product_name: str = ""

    availability: str = "available"

    currency: str = "INR"


# ============================================================
# MERCHANT DECISION
# ============================================================

@dataclass
class MerchantDecision:

    decision: str = "REJECT_DISCOUNT"

    approved_discount_percent: float = 0.0

    max_allowed_discount: float = 0.0

    negotiation_allowed: bool = False

    margin_impact: float = 0.0

    reason: str = ""

    merchant_action: str = "REJECT_DISCOUNT"

    approval_status: str = "NOT_REQUIRED"

    def __post_init__(self):
        if not self.decision and self.merchant_action:
            self.decision = self.merchant_action
        if self.decision and not self.merchant_action:
            self.merchant_action = self.decision
        if self.reason and not self.reason.strip():
            self.reason = "No reason provided."

    @property
    def decision_key(self):
        return self.decision

    @decision_key.setter
    def decision_key(self, value):
        self.decision = value

    @property
    def merchant_action_name(self):
        return self.merchant_action

    @merchant_action_name.setter
    def merchant_action_name(self, value):
        self.merchant_action = value


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