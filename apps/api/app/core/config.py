"""Configuration from environment.

Phase 0: Add support for reasoning_effort and fallback LLM model.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings loaded from environment."""

    # App
    app_name: str = "Mupezeni API"
    app_version: str = "0.1.0"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() in {"1", "true"})

    # CORS
    allow_origins: str = field(default_factory=lambda: os.getenv("ALLOW_ORIGINS", "*"))
    frontend_url: str = field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:3000"))

    # Supabase
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

    # LLM (provider-agnostic, any OpenAI-compatible API)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    llm_fallback_model: str = field(default_factory=lambda: os.getenv("LLM_FALLBACK_MODEL", ""))
    llm_reasoning_effort: str = field(default_factory=lambda: os.getenv("LLM_REASONING_EFFORT", "none"))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1000")))
    llm_timeout: int = field(default_factory=lambda: int(os.getenv("LLM_TIMEOUT", "30")))

    # Image model (provider-agnostic: Gemini, OpenAI, etc.)
    image_protocol: str = field(default_factory=lambda: os.getenv("IMAGE_PROTOCOL", ""))  # e.g., "gemini" or "openai"
    image_provider: str = field(default_factory=lambda: os.getenv("IMAGE_PROVIDER", ""))
    image_api_key: str = field(default_factory=lambda: os.getenv("IMAGE_API_KEY", ""))
    image_base_url: str = field(default_factory=lambda: os.getenv("IMAGE_BASE_URL", "https://api.openai.com/v1"))
    image_model: str = field(default_factory=lambda: os.getenv("IMAGE_MODEL", ""))
    image_size: str = field(default_factory=lambda: os.getenv("IMAGE_SIZE", "1024x1024"))
    image_timeout: int = field(default_factory=lambda: int(os.getenv("IMAGE_TIMEOUT", "120")))

    # Connectors
    connector_encryption_keys: str = field(default_factory=lambda: os.getenv("CONNECTOR_ENCRYPTION_KEYS", ""))
    oauth_state_secret: str = field(default_factory=lambda: os.getenv("OAUTH_STATE_SECRET", ""))

    # Meta (Facebook/Instagram/WhatsApp)
    meta_app_id: str = field(default_factory=lambda: os.getenv("META_APP_ID", ""))
    meta_app_secret: str = field(default_factory=lambda: os.getenv("META_APP_SECRET", ""))
    meta_redirect_uri: str = field(default_factory=lambda: os.getenv("META_REDIRECT_URI", ""))
    meta_webhook_verify_token: str = field(default_factory=lambda: os.getenv("META_WEBHOOK_VERIFY_TOKEN", ""))
    meta_graph_version: str = field(default_factory=lambda: os.getenv("META_GRAPH_VERSION", "v18.0"))


settings = Settings()
