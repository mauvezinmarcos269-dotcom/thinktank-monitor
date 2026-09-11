import asyncio

import httpx

from app.core.config import settings

DEFAULT_MODELS = (
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-14B",
    "Qwen/Qwen2.5-14B-Instruct",
)


async def check_model(model_name: str) -> None:
    print()
    print("=" * 70)
    print("MODEL:", model_name)
    print("=" * 70)

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict JSON generator. Return valid JSON only.",
            },
            {
                "role": "user",
                "content": 'Return exactly this JSON object: {"a":"1","b":"2"}',
            },
        ],
        "temperature": 0.0,
        "max_tokens": 500,
        "response_format": {
            "type": "json_object",
        },
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            settings.LLM_BASE_URL,
            headers=headers,
            json=payload,
        )

    print("STATUS:", response.status_code)
    print("RAW RESPONSE:")
    print(response.text)


async def main() -> None:
    for model_name in DEFAULT_MODELS:
        try:
            await check_model(model_name)
        except Exception as exc:
            print("ERROR:", repr(exc))


if __name__ == "__main__":
    asyncio.run(main())
