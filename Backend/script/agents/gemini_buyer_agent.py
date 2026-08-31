import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.genai import types

from providers.gemini import get_gemini_client


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from script.agents.schemas import BuyerIntent
except ImportError:  # pragma: no cover
    from schemas import BuyerIntent


load_dotenv()


class GeminiBuyerAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        try:
            self.client = get_gemini_client()
        except RuntimeError:
            raise

    def _extract_budget(self, text: str):
        patterns = [
            r"under\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
            r"budget\s*(?:is|under|of)?\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
            r"(?:<=|less than|under)\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None

    def _extract_discount(self, text: str):
        discount_words = [
            "discount",
            "off",
            "percent off",
            "% off",
            "negotiate",
            "better price",
            "cheaper",
            "lower price",
            "do better",
            "can you do better",
            "best price",
            "save money",
            "price reduction",
            "deal",
        ]
        if any(word in text for word in discount_words):
            for pattern in [r"(\d{1,2})\s*%", r"(\d{1,2})\s*percent"]:
                matches = re.findall(pattern, text)
                if matches:
                    return float(max(matches))
            return 0.0
        return None

    def _normalize_parsed_intent(self, parsed: dict, user_message: str) -> dict:
        text = user_message.lower()
        parsed = dict(parsed or {})

        if not parsed.get("intent") or parsed.get("intent") == "unclear":
            if any(keyword in text for keyword in ["want", "buy", "need", "purchase", "order", "shop", "looking for"]):
                parsed["intent"] = "purchase"
            else:
                parsed["intent"] = "browse"

        if parsed.get("budget") in (None, ""):
            budget = self._extract_budget(text)
            if budget is not None:
                parsed["budget"] = budget

        if parsed.get("constraints") in (None, "", []):
            if parsed.get("budget") is not None:
                parsed["constraints"] = [f"under ₹{int(parsed['budget'])}"]
            else:
                parsed["constraints"] = []

        if not parsed.get("product_preferences"):
            product_tokens = [
                "running shoes",
                "shoe",
                "headphones",
                "watch",
                "phone",
                "laptop",
                "camera",
                "speaker",
            ]
            found = [token for token in product_tokens if token in text]
            if found:
                parsed["product_preferences"] = found[:3]

        discount_value = self._extract_discount(text)
        if parsed.get("discount_requested") is None:
            parsed["discount_requested"] = bool(discount_value is not None)

        if parsed.get("discount_requested") is True and discount_value is None:
            parsed["discount_requested"] = False

        if parsed.get("discount_requested") is False and discount_value is not None:
            parsed["discount_requested"] = True

        if parsed.get("max_discount_requested") in (None, "", 0):
            if discount_value is not None:
                parsed["max_discount_requested"] = float(discount_value)
            else:
                parsed["max_discount_requested"] = None

        if parsed.get("confidence") is None:
            parsed["confidence"] = 0.7

        confidence = parsed.get("confidence")
        if isinstance(confidence, (int, float)) and confidence > 1:
            if confidence <= 100:
                parsed["confidence"] = confidence / 100
            else:
                raise RuntimeError("Gemini returned an invalid confidence value.")

        if not isinstance(parsed.get("confidence"), (int, float)):
            parsed["confidence"] = 0.7

        parsed["confidence"] = max(0.0, min(float(parsed["confidence"]), 1.0))

        parsed["intent"] = parsed.get("intent") or "PRODUCT_SEARCH"
        parsed["budget_min"] = parsed.get("budget_min", 0.0)
        parsed["budget_max"] = parsed.get("budget_max") or parsed.get("budget") or self._extract_budget(text)
        parsed["currency"] = parsed.get("currency") or "INR"
        parsed["product_category"] = parsed.get("product_category") or "general"
        parsed["discount_value"] = parsed.get("discount_value") or parsed.get("max_discount_requested") or discount_value
        parsed["urgency"] = parsed.get("urgency") or "medium"
        parsed["confidence_score"] = parsed.get("confidence_score", parsed.get("confidence", 0.7))

        return parsed

    def _build_system_prompt(self) -> str:
        return """
You are the Buyer Agent inside AgentCommerce OS.

Convert the customer's message into structured shopping intent.

Return ONLY valid JSON with this structure:

{
    "intent": "purchase | browse | compare | unclear",
    "budget": number or null,
    "urgency": "low | normal | high",
    "discount_requested": true or false,
    "max_discount_requested": number or null,
    "product_preferences": [],
    "constraints": [],
    "confidence": number between 0 and 1
}

Rules:
- Extract the maximum stated budget.
- "under ₹2000" means budget = 2000.
- Extract discount requests accurately.
- Never approve or promise discounts.
- Do not invent preferences.
- Confidence must be a decimal from 0 to 1.
- Never return confidence as 90 or 100.
"""

    def extract_intent(self, user_message: str) -> BuyerIntent:
        if not user_message.strip():
            raise ValueError("Buyer message cannot be empty.")

        chat = self.client.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=self._build_system_prompt(),
                temperature=0,
                response_mime_type="application/json",
            ),
        )

        response = chat.send_message(user_message)
        raw_output = response.text

        print("\n=== GEMINI RAW OUTPUT ===")
        print(raw_output)
        print("========================\n")

        if not raw_output:
            raise RuntimeError("Gemini returned an empty response.")

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid JSON."
            ) from exc

        parsed = self._normalize_parsed_intent(parsed, user_message)
        output = {
            "intent": parsed.get("intent") or "PRODUCT_SEARCH",
            "budget_min": parsed.get("budget_min", 0.0),
            "budget_max": parsed.get("budget_max") or parsed.get("budget") or None,
            "currency": parsed.get("currency") or "INR",
            "product_category": parsed.get("product_category") or "general",
            "discount_requested": bool(parsed.get("discount_requested")),
            "discount_value": parsed.get("discount_value") or parsed.get("max_discount_requested") or None,
            "urgency": parsed.get("urgency") or "medium",
            "confidence_score": parsed.get("confidence_score") if parsed.get("confidence_score") is not None else parsed.get("confidence", 0.7),
            "product_preferences": parsed.get("product_preferences") or [],
            "constraints": parsed.get("constraints") or [],
        }
        return BuyerIntent(**output)


def run_test(agent: GeminiBuyerAgent, message: str):
    print("\n" + "=" * 80)
    print("CUSTOMER")
    print("=" * 80)
    print(message)

    intent = agent.extract_intent(message)

    print("\nGEMINI BUYER AGENT")
    print("=" * 80)
    print(json.dumps(asdict(intent), indent=4, ensure_ascii=False))


if __name__ == "__main__":
    agent = GeminiBuyerAgent()

    test_messages = [
        "I want running shoes under ₹2000.",
        "I like this product but can you give me 10% off?",
        "Give me 50% discount and I'll buy immediately.",
    ]

    for message in test_messages:
        run_test(agent, message)