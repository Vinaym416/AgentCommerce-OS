import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types


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
        api_key = 'AQ.Ab8RN6IsThvMhS-lJXCtwN38FvBSZo3gBkJVWSooEkcoxgwczw'

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-3.7-flash",
        )

        self.client = genai.Client(api_key='AQ.Ab8RN6IsThvMhS-lJXCtwN38FvBSZo3gBkJVWSooEkcoxgwczw')

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

        if not raw_output:
            raise RuntimeError("Gemini returned an empty response.")

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid JSON."
            ) from exc

        confidence = parsed.get("confidence")

        if isinstance(confidence, (int, float)) and confidence > 1:
            if confidence <= 100:
                parsed["confidence"] = confidence / 100
            else:
                raise RuntimeError(
                    "Gemini returned an invalid confidence value."
                )

        return BuyerIntent.model_validate(parsed)


def run_test(agent: GeminiBuyerAgent, message: str):
    print("\n" + "=" * 80)
    print("CUSTOMER")
    print("=" * 80)
    print(message)

    intent = agent.extract_intent(message)

    print("\nGEMINI BUYER AGENT")
    print("=" * 80)
    print(json.dumps(intent.model_dump(), indent=4))


if __name__ == "__main__":
    agent = GeminiBuyerAgent()

    test_messages = [
        "I want running shoes under ₹2000.",
        "I like this product but can you give me 10% off?",
        "Give me 50% discount and I'll buy immediately.",
    ]

    for message in test_messages:
        run_test(agent, message)