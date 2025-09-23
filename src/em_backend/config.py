from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    env: Literal["dev", "prod"] = "dev"

    # Weaviate API keys
    wv_url: str
    wv_api_key: str

    # Open AI API keys
    openai_api_key: str

    # Bing API keys
    tavily_api_key: str

    # Postgres url
    postgres_url: str

    # Deployement config
    allow_origins: str = "*"


settings = Settings()  # type: ignore
