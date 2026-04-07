#!/usr/bin/env python3
"""CLI entry point for the Ground News agent.

Usage:
    # Full run (fetch + cluster + AI enrich)
    python -m em_backend.groundnews_agent.cli

    # Dry run (fetch + cluster only, no Claude API calls)
    python -m em_backend.groundnews_agent.cli --skip-enrich

    # Test with limited stories
    python -m em_backend.groundnews_agent.cli --max-stories 5

    # Fetch only (test RSS feeds)
    python -m em_backend.groundnews_agent.cli --fetch-only
"""
from __future__ import annotations

import argparse
import logging
import sys


def main():
    parser = argparse.ArgumentParser(description="Ground News Agent for Hungarian Elections")
    parser.add_argument("--skip-enrich", action="store_true",
                        help="Skip Claude API calls (test fetcher/clusterer only)")
    parser.add_argument("--max-stories", type=int, default=None,
                        help="Limit number of stories to process")
    parser.add_argument("--fetch-only", action="store_true",
                        help="Only fetch and print articles, don't cluster or enrich")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.fetch_only:
        from .fetcher import fetch_and_enrich
        articles = fetch_and_enrich()
        print(f"\n{'='*60}")
        print(f"Fetched {len(articles)} articles from RSS feeds")
        print(f"{'='*60}")
        for a in articles[:20]:
            img = "IMG" if a.image_url else "   "
            print(f"  [{a.outlet_id:20s}] {img} {a.title[:60]}")
        if len(articles) > 20:
            print(f"  ... and {len(articles) - 20} more")
        return

    from .runner import run_pipeline
    output = run_pipeline(
        skip_enrich=args.skip_enrich,
        max_stories=args.max_stories,
    )
    print(f"\nDone: {output.story_count} stories written to stories.json")


if __name__ == "__main__":
    main()
