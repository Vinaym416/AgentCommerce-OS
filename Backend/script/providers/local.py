import os

from openai import OpenAI


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