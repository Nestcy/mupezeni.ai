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

    # AI models (provider-agnostic). Anything exposing an OpenAI-compatible HTTP API works:
    # set the base URL, key and model name for whichever provider you choose.
    llm_provider: str = ""  # free-text label for logs only
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1000
    llm_timeout: float = 30.0

    image_provider: str = ""  # free-text label for logs only
    image_api_key: str = ""
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = ""
    image_size: str = "1024x1024"
    image_timeout: float = 120.0

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


class HealthCheck(BaseModel):
    status: str
