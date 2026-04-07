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
        cluster_selection_epsilon=0.3,
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
