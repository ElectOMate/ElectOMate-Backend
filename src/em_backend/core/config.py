from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    env: Literal["dev", "prod"] = "prod"

    # Weaviate API keys
    wv_url: str
    wv_api_key: str

    # Open AI API keys
    openai_model_name: str = "gpt-4o"
    openai_api_key: str

    # Postgres url
    postgres_url: str


settings = Settings()  # type: ignore
