import os

try:
    from openai import OpenAI
except ImportError as exc:
    raise ImportError(
        "The OpenAI SDK is missing or too old. Install a compatible version with: "
        "pip install 'openai>=1.0.0,<2'"
    ) from exc


def get_local_client() -> OpenAI:
    token = os.getenv("HF_TOKEN")

    if not token:
        raise RuntimeError("HF_TOKEN is not configured.")

    return OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=token,
    )


def generate_response(message: str) -> str:
    client = get_local_client()

    completion = client.chat.completions.create(
        model="Qwen/Qwen2.5-7B-Instruct:featherless-ai",
        messages=[
            {
                "role": "user",
                "content": message,
            }
        ],
    )

    return completion.choices[0].message.content or ""