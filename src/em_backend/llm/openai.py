import ssl

from httpx import AsyncClient
from langchain_openai import ChatOpenAI

from em_backend.core.config import settings


def get_proxy_http_client() -> AsyncClient:
    import truststore

    return AsyncClient(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        proxy="http://localhost:8070/",
    )


def get_openai_model(*, with_proxy: bool = False) -> ChatOpenAI:
    if with_proxy:
        return ChatOpenAI(
            model=settings.openai_model_name,
            use_responses_api=True,
            http_async_client=get_proxy_http_client(),
        )
    else:
        return ChatOpenAI(model=settings.openai_model_name, use_responses_api=True)
