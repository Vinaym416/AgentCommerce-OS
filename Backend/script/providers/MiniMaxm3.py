import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_response(
    messages: list[Dict[str, str]],
    model: str | None = None,
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "AgentCommerce OS"),
        },
        json={
            "model": model or os.getenv("OPENROUTER_MODEL", "minimax/minimax-m3:free"),
            "messages": messages,
            "reasoning": {"enabled": True},
        },
        timeout=float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30")),
    )
    response.raise_for_status()

    payload: Dict[str, Any] = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no completion choices.")

    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise RuntimeError("OpenRouter returned an empty response.")
    return content
