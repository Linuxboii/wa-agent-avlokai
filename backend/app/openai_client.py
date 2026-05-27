from openai import AsyncOpenAI

from .config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_reply(system_prompt: str, history: list[dict], model: str) -> str:
    """history: list of {role: user|assistant, content: str}, oldest first."""
    messages = [{"role": "system", "content": system_prompt}] + history
    resp = await _get_client().chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=0.5,
        max_tokens=600,
    )
    return (resp.choices[0].message.content or "").strip()


async def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        resp = await _get_client().audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return (resp.text or "").strip()
