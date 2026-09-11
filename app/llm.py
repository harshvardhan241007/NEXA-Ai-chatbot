"""
Thin LLM client.

- Reads provider/key from environment (app.config.settings) - nothing
  is ever hard-coded.
- Uses `requests` directly against the provider's REST API, so no
  extra SDK dependency is required.
- ALWAYS fails soft: any exception (missing key, network error, bad
  response, timeout) results in `None`, and the caller falls back to
  the local rule-based responder. NEXA never crashes just because an
  API call failed.
"""

from typing import Optional
import requests

from .config import settings
from .logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are NEXA, a helpful, concise AI assistant embedded in a chat "
    "app. Answer clearly. If the user supplies 'Context from document:' "
    "material, ground your answer in it and say so if the answer isn't "
    "in the context."
)


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER

    def is_configured(self) -> bool:
        return settings.has_llm_key

    def generate(self, user_message: str, history: str = "", context: str = "") -> Optional[str]:
        if not self.is_configured():
            return None

        prompt_parts = []
        if history:
            prompt_parts.append(f"Conversation so far:\n{history}")
        if context:
            prompt_parts.append(f"Context from document:\n{context}")
        prompt_parts.append(f"User: {user_message}")
        full_prompt = "\n\n".join(prompt_parts)

        try:
            if self.provider == "openai":
                return self._call_openai(full_prompt)
            if self.provider == "anthropic":
                return self._call_anthropic(full_prompt)
        except Exception as exc:  # noqa: BLE001 - deliberate, we always fail soft
            log.warning("LLM call failed, falling back to local mode: %s", exc)
            return None

        return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.7,
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 500,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", [])).strip()


llm_client = LLMClient()
