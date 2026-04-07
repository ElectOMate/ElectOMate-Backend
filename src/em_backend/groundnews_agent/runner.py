"""Main pipeline: fetch → cluster → enrich → output."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .clusterer import (
    backfill,
    cluster_articles,
    load_existing_stories,
)
from .config import STORIES_FILE
from .fetcher import fetch_and_enrich
from .models import StoriesOutput
from .summarizer import enrich_story

log = logging.getLogger(__name__)


def run_pipeline(skip_enrich: bool = False, max_stories: int | None = None) -> StoriesOutput:
    """Execute the full Ground News agent pipeline.

    Args:
        skip_enrich: Skip Claude API calls (for testing fetcher/clusterer only).
        max_stories: Limit number of stories to process (for testing).
    """
    log.info("=== Ground News Agent Pipeline Start ===")

    # 1. Fetch articles from RSS feeds
    log.info("[1/5] Fetching articles from RSS feeds...")
    articles = fetch_and_enrich()
    log.info("Fetched %d articles total", len(articles))

    if not articles:
        log.warning("No articles fetched — aborting pipeline")
        return StoriesOutput(
            generated_at=datetime.now(timezone.utc).isoformat(),
            story_count=0,
            stories=[],
        )

    # 2. Cluster into stories
    log.info("[2/5] Clustering articles into stories...")
    clusters = cluster_articles(articles)
    log.info("Found %d clusters", len(clusters))

    # 3. Backfill into existing stories
    log.info("[3/5] Backfilling into existing stories...")
    existing = load_existing_stories()
    stories = backfill(clusters, existing)

    # Limit for testing
    if max_stories:
        stories = stories[:max_stories]

    # 4. Enrich with AI (summaries, translations, bias analysis)
    if not skip_enrich:
        log.info("[4/5] Enriching %d stories with Claude AI...", len(stories))
        enriched = []
        for i, story in enumerate(stories):
            # Only enrich stories that haven't been enriched yet
            # (have empty AI summary)
            if not story.ai_summary_en:
                log.info("  Enriching story %d/%d: %s", i + 1, len(stories), story.title_en[:50])
                story = enrich_story(story)
            enriched.append(story)
        stories = enriched
    else:
        log.info("[4/5] Skipping AI enrichment (--skip-enrich)")

    # 5. Sort by importance and write output
    stories.sort(key=lambda s: (s.importance_score, s.last_updated), reverse=True)

    output = StoriesOutput(
        generated_at=datetime.now(timezone.utc).isoformat(),
        story_count=len(stories),
        stories=stories,
    )

    log.info("[5/5] Writing %d stories to %s", len(stories), STORIES_FILE)
    STORIES_FILE.write_text(
        json.dumps(output.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log.info("=== Pipeline Complete: %d stories ===", len(stories))
    return output
