"""Cluster articles into stories using embeddings + HDBSCAN, with backfill."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone

import numpy as np

from .config import (
    BACKFILL_SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    MIN_CLUSTER_SIZE,
    MIN_SOURCES_PER_STORY,
    RESEARCH_SIMILARITY_THRESHOLD,
    STORIES_FILE,
)
from .models import FetchedArticle, StoryArticle, StoryCluster, StoriesOutput

log = logging.getLogger(__name__)

# Lazy-load heavy deps
_model = None


def _get_embed_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        log.info("Loading embedding model %s ...", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _slugify(text: str, max_len: int = 60) -> str:
    """Create a URL-safe slug from text."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    text = re.sub(r"[\s_]+", "-", text)
    return text[:max_len].rstrip("-")


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts using sentence-transformers."""
    model = _get_embed_model()
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def cluster_articles(
    articles: list[FetchedArticle],
) -> dict[int, list[FetchedArticle]]:
    """Cluster articles by story using HDBSCAN on embeddings."""
    if len(articles) < 2:
        return {0: articles} if articles else {}

    import hdbscan

    texts = [f"{a.title} {a.summary[:200]}" for a in articles]
    embeddings = embed_texts(texts)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=MIN_CLUSTER_SIZE,
        metric="euclidean",  # embeddings are normalized, so euclidean ≈ cosine
        cluster_selection_epsilon=0.4,
    )
    labels = clusterer.fit_predict(embeddings)

    clusters: dict[int, list[FetchedArticle]] = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(articles[i])

    # Include noise (-1) articles as single-article stories
    # but only if they have substantial content
    if -1 in clusters:
        noise = clusters.pop(-1)
        for i, article in enumerate(noise):
            if len(article.summary) > 100 or len(article.full_text) > 200:
                clusters[1000 + i] = [article]

    # Filter: skip clusters where all articles are from the same outlet
    filtered = {}
    for label, arts in clusters.items():
        outlet_ids = {a.outlet_id for a in arts}
        if len(outlet_ids) >= 2 or len(arts) == 1:
            filtered[label] = arts

    log.info("Clustered %d articles into %d stories (%d multi-source)",
             len(articles), len(filtered),
             sum(1 for arts in filtered.values() if len({a.outlet_id for a in arts}) >= 2))
    return filtered


def load_existing_stories() -> list[StoryCluster]:
    """Load previously generated stories from disk."""
    if not STORIES_FILE.exists():
        return []
    try:
        data = json.loads(STORIES_FILE.read_text(encoding="utf-8"))
        output = StoriesOutput(**data)
        return output.stories
    except Exception as exc:
        log.warning("Failed to load existing stories: %s", exc)
        return []


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def backfill(
    new_clusters: dict[int, list[FetchedArticle]],
    existing_stories: list[StoryCluster],
) -> list[StoryCluster]:
    """Merge new article clusters into existing stories where similar."""
    if not existing_stories:
        return clusters_to_raw_stories(new_clusters)

    # Embed existing story titles for matching
    existing_texts = [f"{s.title_en} {s.title_hu}" for s in existing_stories]
    existing_embeds = embed_texts(existing_texts) if existing_texts else np.array([])

    merged_stories = list(existing_stories)
    new_stories: list[StoryCluster] = []

    for _label, articles in new_clusters.items():
        cluster_text = " ".join(a.title for a in articles[:5])
        cluster_embed = embed_texts([cluster_text])[0]

        best_sim = 0.0
        best_idx = -1
        if len(existing_embeds) > 0:
            for i, ex_embed in enumerate(existing_embeds):
                sim = _cosine_similarity(cluster_embed, ex_embed)
                if sim > best_sim:
                    best_sim = sim
                    best_idx = i

        if best_sim >= BACKFILL_SIMILARITY_THRESHOLD and best_idx >= 0:
            # Merge into existing story
            story = merged_stories[best_idx]
            existing_urls = {a.url for a in story.articles}
            for article in articles:
                if article.url not in existing_urls:
                    story.articles.append(_fetched_to_story_article(article))
                    existing_urls.add(article.url)
            story.source_count = len(story.articles)
            story.last_updated = datetime.now(timezone.utc).isoformat()
            log.info("Backfilled %d articles into existing story: %s",
                     len(articles), story.title_en[:50])
        else:
            # New story
            new_stories.extend(clusters_to_raw_stories({0: articles}))

    merged_stories.extend(new_stories)

    # Deduplicate articles within each story by URL
    for story in merged_stories:
        seen: set[str] = set()
        deduped: list[StoryArticle] = []
        for a in story.articles:
            if a.url not in seen:
                seen.add(a.url)
                deduped.append(a)
        story.articles = deduped
        story.source_count = len(deduped)

    log.info("After backfill: %d total stories (%d new)", len(merged_stories), len(new_stories))
    return merged_stories


def _fetched_to_story_article(fa: FetchedArticle) -> StoryArticle:
    """Convert a FetchedArticle to a StoryArticle (pre-translation)."""
    return StoryArticle(
        outlet_id=fa.outlet_id,
        headline_en=fa.title,  # Will be translated by summarizer
        headline_hu=fa.title,
        summary_en=fa.summary[:300],
        summary_hu=fa.summary[:300],
        url=fa.url,
        image_url=fa.image_url,
        date=fa.published,
        stance="neutral",
    )


def clusters_to_raw_stories(
    clusters: dict[int, list[FetchedArticle]],
) -> list[StoryCluster]:
    """Convert raw clusters to StoryCluster objects (before AI enrichment)."""
    now = datetime.now(timezone.utc).isoformat()
    stories: list[StoryCluster] = []

    for _label, articles in clusters.items():
        if not articles:
            continue

        first = articles[0]
        story_id = _slugify(first.title) + "-" + now[:10]

        # Pick best image (prefer articles with images)
        image = next((a.image_url for a in articles if a.image_url), None)

        story = StoryCluster(
            id=story_id,
            title_en=first.title,
            title_hu=first.title,
            image_url=image,
            articles=[_fetched_to_story_article(a) for a in articles],
            source_count=len(articles),
            first_seen=now,
            last_updated=now,
        )
        stories.append(story)

    return stories


def research_thin_stories(
    stories: list[StoryCluster],
    all_articles: list[FetchedArticle],
) -> list[StoryCluster]:
    """Deep research pass: find additional sources for stories with < MIN_SOURCES_PER_STORY.

    For each thin story, scan ALL fetched articles using semantic similarity
    with a loose threshold to find related coverage that HDBSCAN missed.
    Prioritises outlet diversity — won't add a second article from the same outlet.
    """
    if not stories or not all_articles:
        return stories

    # Build a URL set of all articles already assigned to any story
    assigned_urls: set[str] = set()
    for s in stories:
        for a in s.articles:
            assigned_urls.add(a.url)

    # Pre-compute embeddings for all fetched articles (cached for reuse)
    article_texts = [f"{a.title} {a.summary[:200]}" for a in all_articles]
    article_embeds = embed_texts(article_texts)

    thin_count = sum(1 for s in stories if len({a.outlet_id for a in s.articles}) < MIN_SOURCES_PER_STORY)
    log.info("Deep research: %d stories have < %d sources, scanning %d articles...",
             thin_count, MIN_SOURCES_PER_STORY, len(all_articles))

    enriched = 0
    for story in stories:
        current_outlets = {a.outlet_id for a in story.articles}
        if len(current_outlets) >= MIN_SOURCES_PER_STORY:
            continue

        # Embed the story for matching
        story_text = f"{story.title_en} {story.title_hu} {story.ai_summary_en or ''}"
        story_embed = embed_texts([story_text])[0]

        existing_urls = {a.url for a in story.articles}

        # Score all fetched articles against this story
        candidates: list[tuple[FetchedArticle, float]] = []
        for j, article in enumerate(all_articles):
            if article.url in existing_urls:
                continue
            # Skip if this outlet is already in the story
            if article.outlet_id in current_outlets:
                continue
            sim = float(np.dot(story_embed, article_embeds[j]))  # normalized → dot = cosine
            if sim >= RESEARCH_SIMILARITY_THRESHOLD:
                candidates.append((article, sim))

        # Sort by similarity descending, add until we hit MIN_SOURCES
        candidates.sort(key=lambda x: x[1], reverse=True)

        added = 0
        for article, sim in candidates:
            if len(current_outlets) >= MIN_SOURCES_PER_STORY:
                break
            if article.outlet_id in current_outlets:
                continue
            story.articles.append(_fetched_to_story_article(article))
            current_outlets.add(article.outlet_id)
            added += 1

        if added > 0:
            story.source_count = len(story.articles)
            story.last_updated = datetime.now(timezone.utc).isoformat()
            enriched += 1
            log.debug("  +%d sources for story: %s (now %d outlets)",
                      added, story.title_en[:50], len(current_outlets))

    log.info("Deep research complete: enriched %d stories", enriched)
    return stories
