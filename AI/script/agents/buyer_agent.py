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

Convert the customer's message into structured shopping intent.

Return ONLY valid JSON:

{
    "intent": "purchase | browse | compare | unclear",
    "budget": number or null,
    "urgency": "low | normal | high",
    "discount_requested": true or false,
    "max_discount_requested": number or null,
    "product_preferences": [],
    "constraints": [],
    "confidence": number
}

Rules:
- Extract the maximum stated budget.
- "under ₹2000" means budget = 2000.
- Extract discount requests accurately.
- Never approve or promise discounts.
- Do not invent preferences.
"""

    def _fallback_intent(self, message: str) -> BuyerIntent:
        text = message.lower()
        budget = None

        for pattern in [
            r"under\s*(?:inr|rs|₹)?\s*([0-9]+)",
            r"budget\s*(?:is|under|of)?\s*(?:inr|rs|₹)?\s*([0-9]+)",
            r"(?:<=|less than|under)\s*(?:inr|rs|₹)?\s*([0-9]+)",
        ]:
            import re
            match = re.search(pattern, text)
            if match:
                budget = float(match.group(1))
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
            ]
        )

        max_discount_requested = None
        for pattern in [
            r"(\d{1,2})\s*%",
            r"(\d{1,2})\s*percent",
        ]:
            import re
            matches = re.findall(pattern, text)
            if matches:
                max_discount_requested = float(max(matches))
                break

        if "immediately" in text or "urgent" in text or "right now" in text:
            urgency = "high"
        elif "soon" in text or "asap" in text:
            urgency = "normal"
        else:
            urgency = "normal"

        return BuyerIntent(
            intent="purchase" if budget is not None or "want" in text or "buy" in text else "browse",
            budget=budget,
            urgency=urgency,
            discount_requested=discount_requested,
            max_discount_requested=max_discount_requested,
            product_preferences=[],
            constraints=[],
            confidence=0.72,
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

        confidence = parsed.get("confidence")

        if isinstance(confidence, (int, float)) and confidence > 1:
            if confidence <= 100:
                parsed["confidence"] = confidence / 100
            else:
                return self._fallback_intent(user_message)

        return BuyerIntent(**parsed)

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