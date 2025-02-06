import openai
import cohere
import weaviate
import weaviate.classes as wvc

from pydantic_settings import BaseSettings, SettingsConfigDict

FILE_CHUNK_SIZE = 1024 * 1024

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class Settings(BaseSettings):
    # Weaviate API keys
    weaviate_host: str
    weaviate_port: int
    weaviate_grpc_host: str
    weaviate_grpc_port: int
    weaviate_api_key: str

    # Cohere API keys
    command_r_url: str
    command_r_api_key: str
    command_r_plus_url: str = ""
    command_r_plus_api_key: str = ""
    embed_english_url: str = ""
    embed_english_api_key: str = ""
    embed_multilingual_url: str
    embed_multilingual_api_key: str
    rerank_english_url: str = ""
    rerank_english_api_key: str = ""
    rerank_multilingual_url: str
    rerank_multilingual_api_key: str

    # Open AI API keys
    openai_api_key: str

    # Deployement config
    allow_origins: str = "*"
    prod: bool

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

cohere_async_clients = {
    "command_r_async_client": cohere.AsyncClientV2(
        api_key=settings.command_r_api_key, base_url=settings.command_r_url
    ),
    "command_r_plus_async_client": cohere.AsyncClientV2(
        api_key=settings.command_r_plus_api_key,
        base_url=settings.command_r_plus_url,
    ),
    "embed_english_async_client": cohere.AsyncClientV2(
        api_key=settings.embed_english_api_key, base_url=settings.embed_english_url
    ),
    "embed_multilingual_async_client": cohere.AsyncClientV2(
        api_key=settings.embed_multilingual_api_key,
        base_url=settings.embed_multilingual_url,
    ),
    "rerank_english_async_client": cohere.AsyncClientV2(
        api_key=settings.rerank_english_api_key,
        base_url=settings.rerank_english_url,
    ),
    "rerank_multilingual_async_client": cohere.AsyncClientV2(
        api_key=settings.rerank_multilingual_api_key,
        base_url=settings.rerank_multilingual_url,
    ),
}

weaviate_async_client = weaviate.use_async_with_custom(
    http_host=settings.weaviate_host,
    http_port=settings.weaviate_port,
    http_secure=False,
    grpc_host=settings.weaviate_grpc_host,
    grpc_port=settings.weaviate_grpc_port,
    grpc_secure=False,
    auth_credentials=wvc.init.Auth.api_key(settings.weaviate_api_key),
    additional_config=wvc.init.AdditionalConfig(timeout=wvc.init.Timeout(init=30, query=60, insert=120)),
)

openai_async_client = openai.AsyncClient(api_key=settings.openai_api_key)
