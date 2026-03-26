from typing import Literal

import truststore
from pydantic_settings import BaseSettings

# Use system certificates
truststore.inject_into_ssl()


class Settings(BaseSettings):
    # Environment
    env: Literal["dev", "prod"] = "prod"

    # Weaviate API keys
    wv_url: str
    wv_api_key: str

    # Open AI API keys
    openai_model_name: str = "gpt-4o"
    openai_api_key: str

    # Perplexity API
    perplexity_api_key: str | None = None
    perplexity_model: str = "sonar"

    # Postgres url
    postgres_url: str

    # Apache AGE graph database (separate PG instance with AGE extension)
    age_postgres_url: str = "host=age-postgres port=5432 dbname=age_graph user=postgres password=postgres"

    # Google Gemini API (for YouTube video transcription)
    google_api_key: str | None = None

    # Hungarian Parliament API token
    parliament_hu_api_token: str | None = None


settings = Settings()  # type: ignore
