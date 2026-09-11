"""Application configuration, loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SIH26105 CRQ Platform"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://crq:crq@localhost:5432/crq"
    cors_origins: str = "http://localhost:3000"
    admin_secret: str = "change-me"

    nvd_api_key: str | None = None

    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # --- AI layer -----------------------------------------------------------------
    ai_enabled: bool = True
    ai_timeout: float = 30.0
    ai_max_steps: int = 4
    ai_groq_model: str = "llama-3.3-70b-versatile"
    ai_gemini_model: str = "gemini-2.0-flash"
    ai_openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    ai_ollama_model: str = "llama3.2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
