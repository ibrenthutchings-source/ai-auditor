import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Local LLM (Railway private network, see infra/railway.toml)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama.railway.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Phase 1 uses an OpenAI-compatible model to validate graph routing
    # before the local 8B model is wired in (Phase 2).
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ai_auditor")

    # Per-regulatory-context HITL thresholds: (max approval_rate, max median_seconds_to_approve)
    # below which rubber-stamping is flagged. Not hardcoded in the agent itself.
    HITL_RUBBER_STAMP_THRESHOLDS: dict[str, tuple[float, float]] = {
        "default": (1.0, 2.0),
    }


settings = Settings()
