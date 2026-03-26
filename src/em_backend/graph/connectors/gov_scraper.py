"""Government document scraper using Browser Use and Playwright.

Scrapes Hungarian government websites for political content:
- kormany.hu — government press releases, decrees
- parlament.hu — public parliamentary documents
- Hungarian news sites (telex.hu, 444.hu, hvg.hu) — political articles
"""

from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import structlog

from em_backend.graph.connectors.base import (
    IngestedDocument,
    Modality,
    SourceType,
    TextSegment,
)

logger = structlog.get_logger(__name__)

# Browser Use API configuration
BROWSERUSE_API_URL = "https://api.browser-use.com/api/v1"


async def _browseruse_extract(
    url: str,
    task: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run a Browser Use task to extract content from a URL.

    Args:
        url: Target URL to scrape.
        task: Natural language description of what to extract.
        api_key: Browser Use API key. Falls back to BROWSERUSE_API_KEY env var.

    Returns:
        Browser Use task result dict.
    """
    key = api_key or os.environ.get("BROWSERUSE_API_KEY", "")
    if not key:
        raise ValueError("BROWSERUSE_API_KEY not configured")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create task
        resp = await client.post(
            f"{BROWSERUSE_API_URL}/tasks",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "task": f"Navigate to {url} and {task}",
                "save_browser_data": False,
            },
        )
        resp.raise_for_status()
        task_data = resp.json()
        task_id = task_data["id"]

        # Poll for completion
        import asyncio
        for _ in range(60):  # Max 5 minutes
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"{BROWSERUSE_API_URL}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {key}"},
            )
            status_resp.raise_for_status()
            result = status_resp.json()
            if result.get("status") in ("completed", "failed"):
                return result

        return {"status": "timeout", "output": None}


async def scrape_kormany_hu_article(url: str) -> IngestedDocument:
    """Scrape a single article from kormany.hu.

    Args:
        url: Full URL to a kormany.hu article/press release.

    Returns:
        IngestedDocument with extracted content.
    """
    logger.info("Scraping kormany.hu article", url=url)

    result = await _browseruse_extract(
        url=url,
        task=(
            "Extract the full article text, title, date, and any speaker/author names. "
            "Return the article title, publication date (YYYY-MM-DD format), "
            "the full article text, and any named speakers or officials mentioned."
        ),
    )

    output = result.get("output", "") or ""
    title = _extract_title(output) or url.split("/")[-1]
    article_date = _extract_date(output)

    return IngestedDocument(
        source_type=SourceType.PRESS_RELEASE,
        modality=Modality.HTML,
        source_url=url,
        title=title,
        date=article_date,
        language="hu",
        segments=[TextSegment(text=output)],
        raw_text=output,
        metadata={"source_site": "kormany.hu"},
    )


async def scrape_news_article(url: str, source_site: str = "telex.hu") -> IngestedDocument:
    """Scrape a political news article from Hungarian media.

    Args:
        url: Full URL to the article.
        source_site: Name of the news outlet.

    Returns:
        IngestedDocument with extracted content.
    """
    logger.info("Scraping news article", url=url, source=source_site)

    result = await _browseruse_extract(
        url=url,
        task=(
            "Extract the article title, publication date, author, "
            "and full article body text. If there are quotes from politicians, "
            "identify the speaker name and their party affiliation."
        ),
    )

    output = result.get("output", "") or ""
    title = _extract_title(output) or url.split("/")[-1]
    article_date = _extract_date(output)

    return IngestedDocument(
        source_type=SourceType.NEWS,
        modality=Modality.HTML,
        source_url=url,
        title=title,
        date=article_date,
        language="hu",
        segments=[TextSegment(text=output)],
        raw_text=output,
        metadata={"source_site": source_site},
    )


async def scrape_parlament_document(url: str) -> IngestedDocument:
    """Scrape a public document from parlament.hu.

    For PDFs, downloads and extracts text. For HTML pages, extracts content.

    Args:
        url: Full URL to the parliament document.

    Returns:
        IngestedDocument with extracted content.
    """
    logger.info("Scraping parlament.hu document", url=url)

    if url.lower().endswith(".pdf"):
        return await _download_and_extract_pdf(url)

    result = await _browseruse_extract(
        url=url,
        task=(
            "Extract the document title, type, date, and full text content. "
            "If this is a bill or resolution, also extract the proposer name "
            "and committee information."
        ),
    )

    output = result.get("output", "") or ""
    title = _extract_title(output) or "Parliamentary Document"

    return IngestedDocument(
        source_type=SourceType.DOCUMENT,
        modality=Modality.HTML,
        source_url=url,
        title=title,
        language="hu",
        segments=[TextSegment(text=output)],
        raw_text=output,
        metadata={"source_site": "parlament.hu"},
    )


async def _download_and_extract_pdf(url: str) -> IngestedDocument:
    """Download a PDF and extract text using pdfplumber."""
    import pdfplumber
    import tempfile

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        segments = []
        full_text_parts = []
        with pdfplumber.open(tmp_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    segments.append(TextSegment(
                        text=text.strip(),
                        page_number=i,
                    ))
                    full_text_parts.append(text.strip())

        return IngestedDocument(
            source_type=SourceType.DOCUMENT,
            modality=Modality.PDF,
            source_url=url,
            title=url.split("/")[-1].replace(".pdf", ""),
            language="hu",
            segments=segments,
            raw_text="\n\n".join(full_text_parts),
            metadata={"source_site": "parlament.hu", "page_count": len(segments)},
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _extract_title(text: str) -> str | None:
    """Try to extract a title from the first line of text."""
    lines = text.strip().split("\n")
    if lines:
        first_line = lines[0].strip()
        if len(first_line) < 200:
            return first_line
    return None


def _extract_date(text: str) -> date | None:
    """Try to extract a date in YYYY-MM-DD format from text."""
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    # Try Hungarian date format: YYYY. MM. DD.
    match = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    return None


# ============================================================================
# Convenience functions for batch processing
# ============================================================================

KORMANY_HU_SAMPLE_URLS = [
    # These are example patterns — actual URLs should be discovered dynamically
    "https://kormany.hu/hirek",
]

NEWS_RSS_FEEDS = {
    "telex.hu": "https://telex.hu/rss/belfold",
    "444.hu": "https://444.hu/feed",
    "hvg.hu": "https://hvg.hu/rss/itthon",
    "index.hu": "https://index.hu/24ora/rss/",
}


async def discover_news_urls(
    feed_url: str,
    limit: int = 10,
    political_keywords: list[str] | None = None,
) -> list[str]:
    """Discover political article URLs from RSS feeds.

    Args:
        feed_url: RSS feed URL.
        limit: Max URLs to return.
        political_keywords: Keywords to filter for political content.

    Returns:
        List of article URLs.
    """
    if political_keywords is None:
        political_keywords = [
            "politika", "kormány", "ellenzék", "parlament", "fidesz",
            "tisza", "orbán", "magyar péter", "választás", "törvény",
        ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()

    # Simple XML parsing for RSS <link> and <title> elements
    from lxml import etree
    root = etree.fromstring(resp.content)

    urls = []
    for item in root.iter("item"):
        link_el = item.find("link")
        title_el = item.find("title")
        if link_el is not None and link_el.text:
            title_text = (title_el.text or "").lower()
            if any(kw in title_text for kw in political_keywords):
                urls.append(link_el.text.strip())
                if len(urls) >= limit:
                    break

    logger.info("Discovered political URLs", feed=feed_url, count=len(urls))
    return urls
