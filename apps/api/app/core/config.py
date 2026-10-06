from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "Mupezeni API"
    app_version: str = "0.1.0"
    debug: bool = False
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    jwt_algorithm: str = "HS256"
    allow_origins: str = "http://localhost:3000,http://localhost:5173"

    # Onboarding / connectors. Comma-separated Fernet keys; first encrypts, all decrypt (rotation).
    connector_encryption_keys: str = ""
    oauth_state_secret: str = ""
    frontend_url: str = "http://localhost:3000"
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = ""
    meta_webhook_verify_token: str = ""
    meta_graph_version: str = "v21.0"

    # ── LLM (primary) ──────────────────────────────────────────────────────────
    # Any OpenAI-compatible /chat/completions endpoint works.
    # For Groq: set LLM_BASE_URL=https://api.groq.com/openai/v1
    #           LLM_MODEL=qwen/qwen3.8-27b  (or the Groq model string)
    #           LLM_API_KEY=<groq key>
    llm_provider: str = ""          # free-text label for logs / metrics only
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1000
    llm_timeout: float = 30.0

    # Groq-specific extras (passed through in the request body when non-empty)
    llm_reasoning_effort: str = "none"  # none | low | medium | high  (Groq preview param)

    # Fallback model: used automatically on 429 / 503 from the primary.
    # Must be on the same provider/base_url. Leave blank to disable fallback.
    llm_fallback_model: str = "llama-3.3-70b-versatile"

    # ── Image generation ───────────────────────────────────────────────────────
    # image_protocol selects the adapter:
    #   "openai"  → POST {image_base_url}/images/generations  (default; works with any OpenAI-compat API)
    #   "gemini"  → POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    image_provider: str = ""        # free-text label for logs only
    image_api_key: str = ""
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = ""
    image_size: str = "1024x1024"
    image_timeout: float = 120.0
    image_protocol: str = "openai"  # "openai" | "gemini"

    # ── Error tracking ─────────────────────────────────────────────────────────
    sentry_dsn: str = ""

    # ── Worker / job queue ─────────────────────────────────────────────────────
    worker_id: str = ""             # overridden by WORKER_ID env var in worker_main.py
    worker_poll_interval_s: float = 2.0
    worker_concurrency: int = 4
    worker_job_types: str = ""      # comma-separated; empty = all types

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


class HealthCheck(BaseModel):
    status: str
