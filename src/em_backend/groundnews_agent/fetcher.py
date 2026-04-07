"""Fetch articles from Hungarian news outlet RSS feeds."""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import feedparser

from .config import (
    FETCH_TIMEOUT_SECONDS,
    MAX_ARTICLE_AGE_DAYS,
    MAX_ARTICLES_PER_FEED,
    MAX_CONCURRENT_DOWNLOADS,
    RSS_FEEDS,
)
from .models import FetchedArticle

log = logging.getLogger(__name__)

# Lazy newspaper4k import (heavy dependency)
_Article = None


def _get_article_class():
    global _Article
    if _Article is None:
        from newspaper import Article
        _Article = Article
    return _Article


def _parse_date(date_str: str) -> str | None:
    """Try to parse a date string to ISO format."""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        pass
    try:
        from dateutil.parser import parse as dateparse
        dt = dateparse(date_str)
        return dt.isoformat()
    except Exception:
        return None


def _is_too_old(date_iso: str | None) -> bool:
    """Check if article is older than MAX_ARTICLE_AGE_DAYS."""
    if not date_iso:
        return False  # unknown date = keep it
    try:
        dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
        return dt < cutoff
    except Exception:
        return False


def _slugify(text: str) -> str:
    """Simple slugify for dedup."""
    return re.sub(r"[^a-z0-9]", "", text.lower().strip())


def fetch_feed(outlet_id: str, feed_url: str) -> list[FetchedArticle]:
    """Parse a single RSS feed and return articles."""
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            log.warning("Feed error for %s: %s", outlet_id, feed.bozo_exception)
            return []
    except Exception as exc:
        log.warning("Failed to fetch feed %s: %s", outlet_id, exc)
        return []

    articles: list[FetchedArticle] = []
    for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        if not title or not url:
            continue

        date_raw = entry.get("published") or entry.get("updated") or ""
        date_iso = _parse_date(date_raw)

        if _is_too_old(date_iso):
            continue

        summary = entry.get("summary", "").strip()
        # Strip HTML tags from summary
        summary = re.sub(r"<[^>]+>", "", summary)[:500]

        # Try to get image from enclosure or media:content
        image_url = None
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("image/"):
                image_url = enc.get("href")
                break
        if not image_url:
            media = entry.get("media_content", [])
            if media and isinstance(media, list):
                image_url = media[0].get("url")

        articles.append(FetchedArticle(
            outlet_id=outlet_id,
            title=title,
            url=url,
            summary=summary,
            image_url=image_url,
            published=date_iso or datetime.now(timezone.utc).isoformat(),
        ))

    log.info("Fetched %d articles from %s", len(articles), outlet_id)
    return articles


def fetch_all_feeds() -> list[FetchedArticle]:
    """Fetch articles from all configured RSS feeds."""
    all_articles: list[FetchedArticle] = []
    for outlet_id, feed_url in RSS_FEEDS.items():
        articles = fetch_feed(outlet_id, feed_url)
        all_articles.extend(articles)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    deduped: list[FetchedArticle] = []
    for a in all_articles:
        norm = _slugify(a.url)
        if norm not in seen_urls:
            seen_urls.add(norm)
            deduped.append(a)

    log.info("Total after dedup: %d articles from %d feeds", len(deduped), len(RSS_FEEDS))
    return deduped


def enrich_article(article: FetchedArticle) -> FetchedArticle:
    """Use newspaper4k to extract full text and image."""
    Article = _get_article_class()
    try:
        art = Article(article.url, language="hu")
        art.config.request_timeout = FETCH_TIMEOUT_SECONDS
        art.download()
        art.parse()

        if art.text:
            article.full_text = art.text[:3000]
        if art.top_image and not article.image_url:
            article.image_url = art.top_image
        if not article.summary and art.text:
            article.summary = art.text[:400]

    except Exception as exc:
        log.debug("Enrichment failed for %s: %s", article.url[:80], exc)

    return article


def fetch_and_enrich() -> list[FetchedArticle]:
    """Full pipeline: fetch RSS → enrich with newspaper4k."""
    articles = fetch_all_feeds()

    log.info("Enriching %d articles with newspaper4k...", len(articles))
    enriched: list[FetchedArticle] = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as pool:
        futures = {pool.submit(enrich_article, a): a for a in articles}
        for future in as_completed(futures):
            try:
                enriched.append(future.result())
            except Exception as exc:
                original = futures[future]
                log.warning("Enrich error for %s: %s", original.url[:60], exc)
                enriched.append(original)

    # Sort newest first
    enriched.sort(key=lambda a: a.published, reverse=True)
    log.info("Enrichment complete: %d articles, %d with images",
             len(enriched), sum(1 for a in enriched if a.image_url))
    return enriched
