import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from providers.local import get_local_client
try:
    from script.agents.schemas import BuyerIntent
except ImportError:  # pragma: no cover
    from agents.schemas import BuyerIntent

load_dotenv()


class BuyerAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv(
            "LLM_MODEL",
            "Qwen/Qwen2.5-7B-Instruct:featherless-ai",
        )

        try:
            self.client = get_local_client()
        except Exception:
            self.client = None

    def _build_system_prompt(self) -> str:
        return """
You are the Buyer Agent inside AgentCommerce OS.

Convert the customer's message into structured commercial intent.

Return ONLY valid JSON matching this schema:

{
    "intent": "PRODUCT_SEARCH",
    "budget_min": 0,
    "budget_max": 2000,
    "currency": "INR",
    "product_category": "electronics",
    "discount_requested": true,
    "discount_value": 10,
    "urgency": "medium",
    "confidence_score": 0.95
}

Rules:
- Use intent values like PRODUCT_SEARCH, NEGOTIATE, ACCEPT, CANCEL.
- budget_max is the highest limit the customer mentions.
- If the user asks for a discount, set discount_requested=true and discount_value to the offered percent.
- Use urgency low|medium|high.
- If no explicit budget is given, budget_max can be null.
"""

    def _fallback_intent(self, message: str) -> BuyerIntent:
        text = message.lower()
        budget_max = None

        for pattern in [
            r"under\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
            r"budget\s*(?:is|under|of)?\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
            r"(?:<=|less than|under)\s*(?:inr|rs|₹)?\s*([0-9][0-9,]*)",
        ]:
            import re
            match = re.search(pattern, text)
            if match:
                budget_max = float(match.group(1).replace(",", ""))
                break

        discount_requested = any(
            token in text
            for token in [
                "discount",
                "off",
                "% off",
                "percent off",
                "10%",
                "20%",
                "50%",
                "give me",
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
        )

        discount_value = None
        for pattern in [
            r"(\d{1,2})\s*%",
            r"(\d{1,2})\s*percent",
        ]:
            import re
            matches = re.findall(pattern, text)
            if matches:
                discount_value = float(max(matches))
                break

        if "immediately" in text or "urgent" in text or "right now" in text:
            urgency = "high"
        elif "soon" in text or "asap" in text:
            urgency = "medium"
        else:
            urgency = "medium"

        category = "electronics" if any(token in text for token in ["headphone", "headphones", "phone", "laptop", "speaker", "watch", "camera"]) else "general"

        if budget_max is not None or "want" in text or "buy" in text or "need" in text:
            intent = "PRODUCT_SEARCH"
        elif "accept" in text or "buy it" in text or "take it" in text:
            intent = "ACCEPT"
        elif "cancel" in text or "stop" in text:
            intent = "CANCEL"
        else:
            intent = "PRODUCT_SEARCH"

        return BuyerIntent(
            intent=intent,
            budget_min=0.0,
            budget_max=budget_max,
            currency="INR",
            product_category=category,
            discount_requested=discount_requested,
            discount_value=discount_value,
            urgency=urgency,
            confidence_score=0.72,
            product_preferences=[],
            constraints=[] if budget_max is None else [f"under ₹{int(budget_max)}"],
        )

    def analyze(self, message: str) -> BuyerIntent:
        user_message = message

        if not user_message.strip():
            raise ValueError("Buyer message cannot be empty.")

        if self.client is None:
            return self._fallback_intent(user_message)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._build_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )

            raw_output = completion.choices[0].message.content

        except Exception:
            return self._fallback_intent(user_message)

        if not raw_output:
            raise RuntimeError("Gemini returned an empty response.")

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            return self._fallback_intent(user_message)

        normalized = {
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

        confidence = normalized["confidence_score"]
        if isinstance(confidence, (int, float)) and confidence > 1:
            if confidence <= 100:
                normalized["confidence_score"] = confidence / 100
            else:
                return self._fallback_intent(user_message)

        if not isinstance(normalized["confidence_score"], (int, float)):
            normalized["confidence_score"] = 0.7

        return BuyerIntent(**normalized)

    def extract_intent(self, user_message: str) -> BuyerIntent:
        return self.analyze(user_message)


def run_test(agent: BuyerAgent, message: str):
    print("\n" + "=" * 80)
    print("CUSTOMER")
    print("=" * 80)
    print(message)

    intent = agent.extract_intent(message)

    print("\nBUYER AGENT")
    print("=" * 80)
    print(
        json.dumps(
            intent.model_dump(),
            indent=4,
        )
    )


if __name__ == "__main__":

    agent = BuyerAgent()

    test_messages = [
        "I want running shoes under ₹2000.",

        "I like this product but can you give me 10% off?",

        "Give me 50% discount and I'll buy immediately.",
    ]

    for message in test_messages:
        run_test(
            agent,
            message,
        )