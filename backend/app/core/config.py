import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Local LLM (Railway private network, see infra/railway.toml)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama.railway.internal:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    # Explicit override: "openai" | "anthropic" | "gemini" | "ollama".
    # If unset, get_chat_model() picks the first provider with a key set,
    # in that order, falling back to Ollama.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ai_auditor")

    # Comma-separated list of allowed frontend origins for CORS. Defaults to
    # local Next.js dev only; set to the deployed frontend's origin(s) too
    # once the frontend itself is hosted somewhere.
    CORS_ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ]

    # Per-regulatory-context HITL thresholds: (max approval_rate, max median_seconds_to_approve)
    # below which rubber-stamping is flagged. Not hardcoded in the agent itself.
    HITL_RUBBER_STAMP_THRESHOLDS: dict[str, tuple[float, float]] = {
        "default": (1.0, 2.0),
    }


settings = Settings()
