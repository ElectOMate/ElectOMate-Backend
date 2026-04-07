"""Async Wikipedia client using the MediaWiki Action API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

import httpx


logger = logging.getLogger(__name__)

_USER_AGENT = "ElectOMate/1.0 (https://opendemocracy.ai)"
_MAX_EXTRACT_CHARS = 800
_MAX_RESULTS = 8


@dataclass(slots=True)
class WikipediaResult:
    """A single Wikipedia search result with its extract."""

    title: str
    url: str
    snippet: str
    extract: str


@dataclass(slots=True)
class WikipediaResponse:
    """Wrapper for a Wikipedia search response."""

    query: str
    results: list[WikipediaResult]
    language: str


class WikipediaClient:
    """Minimal async client for the MediaWiki Action API."""

    def __init__(
        self,
        *,
        language: str = "hu",
        timeout: float = 15.0,
    ) -> None:
        self.language = language
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _api_url(self, lang: str | None = None) -> str:
        code = lang or self.language
        return f"https://{code}.wikipedia.org/w/api.php"

    def _article_url(self, title: str, lang: str | None = None) -> str:
        code = lang or self.language
        encoded = quote_plus(title.replace(" ", "_"))
        return f"https://{code}.wikipedia.org/wiki/{encoded}"

    async def search(
        self,
        query: str,
        *,
        language: str | None = None,
        limit: int = _MAX_RESULTS,
    ) -> WikipediaResponse:
        """Search Wikipedia and return results with article extracts.

        Parameters
        ----------
        query:
            The search string.
        language:
            Two-letter Wikipedia language code (e.g. "hu", "de", "en").
            Falls back to the client default.
        limit:
            Maximum number of results to return (capped at 5).
        """
        lang = language or self.language
        limit = min(limit, _MAX_RESULTS)

        # Step 1: search for articles
        search_params: dict[str, Any] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }

        try:
            resp = await self._client.get(self._api_url(lang), params=search_params)
            resp.raise_for_status()
            search_data = resp.json()
        except Exception:
            logger.exception("Wikipedia search request failed for query=%r lang=%s", query, lang)
            return WikipediaResponse(query=query, results=[], language=lang)

        hits = search_data.get("query", {}).get("search", [])
        if not hits:
            logger.info("Wikipedia search returned 0 results for query=%r lang=%s", query, lang)
            return WikipediaResponse(query=query, results=[], language=lang)

        titles = [h["title"] for h in hits]
        snippets_by_title = {h["title"]: h.get("snippet", "") for h in hits}

        # Step 2: fetch intro extracts for all matched titles in one call
        extracts_params: dict[str, Any] = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "exchars": _MAX_EXTRACT_CHARS,
            "titles": "|".join(titles),
            "format": "json",
            "utf8": 1,
        }

        extracts_by_title: dict[str, str] = {}
        try:
            resp = await self._client.get(self._api_url(lang), params=extracts_params)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                page_title = page.get("title", "")
                extract = (page.get("extract") or "")[:_MAX_EXTRACT_CHARS]
                extracts_by_title[page_title] = extract
        except Exception:
            logger.exception("Wikipedia extracts request failed for titles=%s lang=%s", titles, lang)
            # Continue without extracts — we still have snippets

        results: list[WikipediaResult] = []
        for title in titles:
            results.append(
                WikipediaResult(
                    title=title,
                    url=self._article_url(title, lang),
                    snippet=snippets_by_title.get(title, ""),
                    extract=extracts_by_title.get(title, ""),
                )
            )

        logger.info(
            "Wikipedia search returned %d results for query=%r lang=%s",
            len(results),
            query,
            lang,
        )
        return WikipediaResponse(query=query, results=results, language=lang)

    async def search_multiple(
        self,
        queries: list[str],
        *,
        language: str | None = None,
        limit: int = _MAX_RESULTS,
    ) -> list[WikipediaResponse]:
        """Run multiple Wikipedia searches concurrently."""
        if not queries:
            return []
        tasks = [self.search(q, language=language, limit=limit) for q in queries]
        return list(await asyncio.gather(*tasks))
