import json
import os
import re
from typing import Optional

from script.agents.schemas import BuyerIntent
from script.providers.MiniMaxm3 import generate_response


class MiniMaxBuyerAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("OPENROUTER_MODEL", "minimax/minimax-m3:free")

    def _build_system_prompt(self) -> str:
        return """
You are the Buyer Agent inside AgentCommerce OS.

Convert the customer's message into structured commercial intent.
Return ONLY valid JSON with these keys:
{
  "intent": "PRODUCT_SEARCH | NEGOTIATE | ACCEPT | CANCEL | BROWSE",
  "budget_min": number or null,
  "budget_max": number or null,
  "currency": "INR",
  "product_category": string,
  "discount_requested": boolean,
  "discount_value": number or null,
  "urgency": "low | medium | high",
  "confidence_score": number between 0 and 1,
    "result_limit": integer or null,
  "product_preferences": [],
  "constraints": []
}
Do not approve or promise discounts. Extract only information present in the customer message.
""".strip()

    @staticmethod
    def _extract_budget(text: str):
        match = re.search(
            r"(?:under|below|less than|budget(?:\s+is|\s+of)?)\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
            text,
            flags=re.IGNORECASE,
        )
        return float(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _extract_discount(text: str):
        discount_pattern = (
            r"\bdiscount\b|\boff\b|%|\bcheaper\b|\bdeal\b|"
            r"\bbetter\s+price\b|\bnegotiate\b"
        )
        if not re.search(discount_pattern, text, flags=re.IGNORECASE):
            return None
        matches = re.findall(r"(\d{1,2})\s*(?:%|percent)", text)
        return float(max(matches)) if matches else 0.0

    @staticmethod
    def _extract_result_limit(text: str):
        match = re.search(
            r"\b(?:show|give|find|list)\s+(?:me\s+)?(\d+)\s+(?:options?|products?|items?)\b",
            text,
            flags=re.IGNORECASE,
        )
        return max(1, min(50, int(match.group(1)))) if match else None

    def _normalize(self, parsed: dict, message: str) -> dict:
        text = message.lower()
        budget = parsed.get("budget_max") or parsed.get("budget") or self._extract_budget(text)
        discount = self._extract_discount(text)
        result_limit = parsed.get("result_limit") or self._extract_result_limit(text)
        urgency = parsed.get("urgency") or "low"
        if urgency == "normal":
            urgency = "low"
        if urgency not in {"low", "medium", "high"}:
            urgency = "low"

        confidence = parsed.get("confidence_score", parsed.get("confidence", 0.7))
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.7
        if confidence > 1 and confidence <= 100:
            confidence /= 100
        confidence = max(0.0, min(confidence, 1.0))

        discount_requested = parsed.get("discount_requested")
        if discount_requested is None:
            discount_requested = discount is not None
        elif discount is not None:
            discount_requested = True
        discount_value = parsed.get("discount_value") or parsed.get("max_discount_requested")
        if discount_value is None and discount is not None:
            discount_value = discount

        intent = str(parsed.get("intent") or "PRODUCT_SEARCH").upper()
        if intent in {"PURCHASE", "BROWSE", "COMPARE", "UNCLEAR"}:
            intent = {"PURCHASE": "PRODUCT_SEARCH", "BROWSE": "BROWSE", "COMPARE": "PRODUCT_SEARCH", "UNCLEAR": "PRODUCT_SEARCH"}[intent]
        if any(token in text for token in ("cheap", "cheapest", "budget-friendly")) and budget is None:
            parsed.setdefault("product_preferences", []).append("low_price")
        if any(token in text for token in ("good discount", "best discount", "great discount")):
            discount_requested = True
        print(f"Output from MiniMax Buyer Agent: {parsed}")
        return {
            "intent": intent,
            "budget_min": parsed.get("budget_min") or 0.0,
            "budget_max": budget,
            "currency": parsed.get("currency") or "INR",
            "product_category": parsed.get("product_category") or "general",
            "discount_requested": bool(discount_requested),
            "discount_value": discount_value,
            "result_limit": result_limit,
            "urgency": urgency,
            "confidence_score": confidence,
            "product_preferences": parsed.get("product_preferences") or [],
            "constraints": parsed.get("constraints") or ([f"under ₹{int(budget)}"] if budget is not None else []),
        }

    def extract_intent(self, user_message: str) -> BuyerIntent:
        if not user_message.strip():
            raise ValueError("Buyer message cannot be empty.")

        raw_output = generate_response(
            [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_message},
            ],
            model=self.model,
        )
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenRouter MiniMax returned invalid JSON.") from exc
        return BuyerIntent(**self._normalize(parsed, user_message))

    def analyze(self, message: str) -> BuyerIntent:
        return self.extract_intent(message)
