"""
Central configuration for NEXA AI Chatbot.

All secrets/config values are loaded from environment variables (via a
.env file in development). Nothing sensitive is hard-coded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from a .env file if present (does nothing in prod
# environments where real env vars are already set).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "NEXA AI Chatbot")

    # LLM provider: "openai" | "anthropic" | "none"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none").lower()

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "data" / "nexa.db"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "data" / "nexa.log"))

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def has_llm_key(self) -> bool:
        if self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        if self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        return False


settings = Settings()
