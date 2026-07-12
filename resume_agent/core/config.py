from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TAVILY_API_KEY: str = Field(..., description="Tavily API key for web search")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LLM_MODEL: str = Field(default="gemma4:e2b", description="Ollama model name")
    LLM_BASE_URL: str = Field(default="http://localhost:11434/v1", description="Ollama API base URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
