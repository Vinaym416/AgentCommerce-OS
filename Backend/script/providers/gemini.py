import os

from google import genai


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("Gemini_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Set Gemini_API_KEY or GEMINI_API_KEY in your environment."
        )

    return genai.Client(api_key=api_key)
