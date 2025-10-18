from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import logging
import httpx


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PerplexitySource:
    """Normalized representation of a Perplexity citation/search result."""

    title: str
    url: str
    snippet: str = ""
    published_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PerplexityResponse:
    """Wrapper for Perplexity responses used by the agent."""

    query: str
    answer: str
    sources: list[PerplexitySource]
    raw: Mapping[str, Any]


class PerplexityClient:
    """Minimal async client for the Perplexity REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "sonar",
        base_url: str = "https://api.perplexity.ai",
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def create_completion(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
        model: str | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        max_output_tokens: int | None = None,
        stream: bool = False,
        **extra: Any,
    ) -> Mapping[str, Any]:
        """Invoke the Perplexity chat completion endpoint."""

        payload: dict[str, Any] = {
            "model": model or self.model,
            "temperature": temperature,
            "messages": list(messages),
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens
        if stream:
            payload["stream"] = True
        if extra:
            payload.update(extra)

        url = f"{self.base_url}/chat/completions"
        logger.debug(
            "Calling Perplexity completion: url=%s model=%s stream=%s extras=%s",
            url,
            payload["model"],
            stream,
            {k: v for k, v in extra.items() if k not in {"messages"}},
        )

        response = await self._client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
