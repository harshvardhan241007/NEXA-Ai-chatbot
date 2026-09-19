"""
NEXA LLM client.

Supports:
- Gemini
- OpenAI
- Anthropic

Gemini is automatically used when GEMINI_API_KEY
is available in the environment.

All API calls fail softly so NEXA can fall back
to the local responder if an API is unavailable.
"""

from typing import Optional
import os
import requests

from .config import settings
from .logger import get_logger

log = get_logger(__name__)


SYSTEM_PROMPT = (
    "You are NEXA, a helpful AI assistant embedded in a chat app. "
    "Answer clearly, naturally and accurately. "
    "Keep answers easy to understand unless the user asks for detail. "
    "For coding questions, provide useful code and explanations. "
    "If the user provides document context, use that context to answer. "
    "Do not invent information that is not supported by the provided context."
)


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER

        # Gemini configuration
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def is_configured(self) -> bool:
        # Gemini key takes priority if available.
        if self.gemini_api_key:
            return True

        # Keep existing OpenAI/Anthropic behaviour.
        return settings.has_llm_key

    def generate(
        self,
        user_message: str,
        history: str = "",
        context: str = "",
    ) -> Optional[str]:

        if not self.is_configured():
            return None

        prompt_parts = []

        if history:
            prompt_parts.append(
                f"Conversation so far:\n{history}"
            )

        if context:
            prompt_parts.append(
                f"Context from document:\n{context}"
            )

        prompt_parts.append(
            f"User: {user_message}"
        )

        full_prompt = "\n\n".join(prompt_parts)

        try:
            # Gemini takes priority when GEMINI_API_KEY exists.
            if self.gemini_api_key:
                return self._call_gemini(full_prompt)

            if self.provider == "openai":
                return self._call_openai(full_prompt)

            if self.provider == "anthropic":
                return self._call_anthropic(full_prompt)

        except Exception as exc:
            log.warning(
                "LLM call failed, falling back to local mode: %s",
                exc
            )
            return None

        return None

    # ------------------------------------------------------------------
    # GEMINI
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> Optional[str]:

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.gemini_model}:generateContent"
        )

        headers = {
            "x-goog-api-key": self.gemini_api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": SYSTEM_PROMPT
                    }
                ]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
            },
        }

        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        resp.raise_for_status()

        data = resp.json()

        candidates = data.get("candidates", [])

        if not candidates:
            log.warning("Gemini returned no candidates.")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])

        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not text:
            log.warning("Gemini returned an empty response.")
            return None

        return text

    # ------------------------------------------------------------------
    # OPENAI
    # ------------------------------------------------------------------

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
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                "max_tokens": 500,
                "temperature": 0.7,
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        resp.raise_for_status()

        data = resp.json()

        return (
            data["choices"][0]["message"]["content"]
            .strip()
        )

    # ------------------------------------------------------------------
    # ANTHROPIC
    # ------------------------------------------------------------------

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
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            },
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )

        resp.raise_for_status()

        data = resp.json()

        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
        ).strip()


llm_client = LLMClient()