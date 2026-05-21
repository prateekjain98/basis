"""App settings from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    tavily_api_key: str = ""
    llama_cloud_api_key: str = ""

    supabase_url: str = ""
    supabase_key: str = ""

    qdrant_url: str = "http://localhost:6333"


settings = Settings()
