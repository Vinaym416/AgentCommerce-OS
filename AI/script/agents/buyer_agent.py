import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parents[1]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from providers.local import get_local_client
from schemas import BuyerIntent

load_dotenv()


class BuyerAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv(
            "LLM_MODEL",
            "Qwen/Qwen2.5-7B-Instruct:featherless-ai",
        )

        self.client = get_local_client()

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

    def analyze(self, message: str) -> BuyerIntent:
        user_message = message

        if not user_message.strip():
            raise ValueError("Buyer message cannot be empty.")

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

        except Exception as exc:
            raise RuntimeError(
                f"Gemini request failed: {exc}"
            ) from exc

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