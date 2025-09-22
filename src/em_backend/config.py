import openai
import weaviate
import weaviate.classes as wvc
from pydantic_settings import BaseSettings, SettingsConfigDict
from tavily import AsyncTavilyClient

from em_backend.langchain_citation_client import LangChainAsyncCitationClient

FILE_CHUNK_SIZE = 1024 * 1024

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class Settings(BaseSettings):
    # Weaviate API keys
    wv_url: str
    wv_http_host: str
    wv_http_port: int
    wv_grpc_host: str
    wv_grpc_port: int
    wv_api_key: str

    # Open AI API keys
    openai_api_key: str

    # Bing API keys
    tavily_api_key: str

    # Deployement config
    allow_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore


weaviate_async_client = weaviate.use_async_with_custom(
    http_host=settings.wv_http_host,
    http_port=settings.wv_http_port,
    http_secure=False,
    grpc_host=settings.wv_grpc_host,
    grpc_port=settings.wv_grpc_port,
    grpc_secure=False,
    auth_credentials=wvc.init.Auth.api_key(settings.wv_api_key),
    additional_config=wvc.init.AdditionalConfig(
        timeout=wvc.init.Timeout(init=30, query=60, insert=120)
    ),
)

openai_async_client = openai.AsyncClient(api_key=settings.openai_api_key)

# LangChain Citation Client wrapper
langchain_citation_client = LangChainAsyncCitationClient(
    api_key=settings.openai_api_key
)

# LangChain async clients dictionary
langchain_async_clients = {
    "langchain_chat_client": langchain_citation_client,
    "embed_client": None,  # Will be handled by third-party service
    "rerank_client": None,  # Will be handled by third-party service
}

# Instantiate Bing client
tavily_client = AsyncTavilyClient(settings.tavily_api_key)

# Export clients
__all__ = [
    "settings",
    "weaviate_async_client",
    "openai_async_client",
    "langchain_citation_client",
    "langchain_async_clients",
    "tavily_client",
]
