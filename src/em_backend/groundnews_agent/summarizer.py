"""AI summarization, translation, topic tagging, and bias analysis."""
from __future__ import annotations

import json
import logging
import os

from anthropic import Anthropic

from .config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL, ELECTION_TOPICS, OUTLETS_FILE, TOPIC_KEYWORDS
from .models import (
    BlindspotInfo,
    ClaudeArticleBatch,
    ClaudeStoryMeta,
    StoryCluster,
)

log = logging.getLogger(__name__)

# Bias tiers grouped for blindspot computation
PRO_GOV_TIERS = {"pro_government", "lean_government"}
INDEPENDENT_TIERS = {"center", "lean_independent", "independent", "opposition"}

_outlets_cache: dict | None = None


def _load_outlets() -> dict[str, dict]:
    """Load outlets.json as a dict keyed by outlet ID."""
    global _outlets_cache
    if _outlets_cache is not None:
        return _outlets_cache
    if OUTLETS_FILE.exists():
        data = json.loads(OUTLETS_FILE.read_text(encoding="utf-8"))
        _outlets_cache = {o["id"]: o for o in data}
    else:
        _outlets_cache = {}
    return _outlets_cache


def _get_client() -> Anthropic:
    """Create Anthropic client."""
    return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def summarize_story(story: StoryCluster) -> StoryCluster:
    """Use Claude to generate title, summary, topic tags, importance."""
    outlets = _load_outlets()
    client = _get_client()

    article_descriptions = []
    for a in story.articles[:15]:  # cap to avoid token overrun
        outlet = outlets.get(a.outlet_id, {})
        outlet_name = outlet.get("name", a.outlet_id)
        bias = outlet.get("bias", "unknown")
        desc = f"- [{outlet_name}] (bias: {bias}) \"{a.headline_hu}\"\n  {a.summary_hu[:200]}"
        article_descriptions.append(desc)

    prompt = f"""You are a neutral news analyst covering the 2026 Hungarian elections.

Given these articles from different Hungarian news outlets about the same story, generate:
1. A concise story TITLE in English and Hungarian (max 15 words each)
2. A neutral 2-3 sentence SUMMARY synthesizing all perspectives (in both languages)
3. Which election topics this relates to (choose from: {', '.join(ELECTION_TOPICS)})
4. An importance score 1-10 for the Hungarian 2026 election context

Articles:
{chr(10).join(article_descriptions)}
"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "output_story_meta",
                "description": "Output the story metadata",
                "input_schema": ClaudeStoryMeta.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "output_story_meta"},
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                meta = ClaudeStoryMeta(**block.input)
                story.title_en = meta.title_en
                story.title_hu = meta.title_hu
                story.ai_summary_en = meta.summary_en
                story.ai_summary_hu = meta.summary_hu
                story.topic_tags = [t for t in meta.topic_tags if t in ELECTION_TOPICS]
                story.importance_score = meta.importance_score
                break

    except Exception as exc:
        log.error("Claude summary failed for story %s: %s", story.id[:40], exc)
        # Fallback: auto-tag topics by keyword matching
        story.topic_tags = _auto_tag_topics(story)

    return story


def translate_articles(story: StoryCluster) -> StoryCluster:
    """Use Claude to translate article headlines and detect stance."""
    if not story.articles:
        return story

    client = _get_client()
    outlets = _load_outlets()

    # Build article list for translation
    article_list = []
    for i, a in enumerate(story.articles[:15]):
        outlet = outlets.get(a.outlet_id, {})
        bias = outlet.get("bias", "unknown")
        article_list.append(
            f"{i}. [{outlet.get('name', a.outlet_id)}] (bias: {bias})\n"
            f"   Headline: {a.headline_hu}\n"
            f"   Summary: {a.summary_hu[:200]}"
        )

    prompt = f"""Translate these Hungarian news article headlines and summaries to English.
Also determine each article's stance on the story: "for" (supports government position),
"against" (opposes government position), "neutral", or "mixed".

If text is already in English, provide the Hungarian translation instead.

Articles:
{chr(10).join(article_list)}

Return exactly {len(article_list)} translations in order."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "output_translations",
                "description": "Output article translations",
                "input_schema": ClaudeArticleBatch.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "output_translations"},
        )

        for block in response.content:
            if block.type == "tool_use":
                batch = ClaudeArticleBatch(**block.input)
                for i, trans in enumerate(batch.articles):
                    if i < len(story.articles):
                        story.articles[i].headline_en = trans.headline_en
                        story.articles[i].headline_hu = trans.headline_hu
                        story.articles[i].summary_en = trans.summary_en
                        story.articles[i].summary_hu = trans.summary_hu
                        story.articles[i].stance = trans.stance
                break

    except Exception as exc:
        log.error("Claude translation failed for story %s: %s", story.id[:40], exc)

    return story


def compute_bias_distribution(story: StoryCluster) -> dict[str, int]:
    """Count articles per bias tier."""
    outlets = _load_outlets()
    dist: dict[str, int] = {
        "pro_government": 0,
        "lean_government": 0,
        "center": 0,
        "lean_independent": 0,
        "independent": 0,
        "opposition": 0,
    }
    for a in story.articles:
        outlet = outlets.get(a.outlet_id, {})
        bias = outlet.get("bias", "")
        if bias in dist:
            dist[bias] += 1
    return dist


def compute_blindspot(dist: dict[str, int]) -> BlindspotInfo:
    """Determine if there's a blindspot in coverage."""
    total = sum(dist.values())
    if total == 0:
        return BlindspotInfo()

    pro_gov = dist.get("pro_government", 0) + dist.get("lean_government", 0)
    independent = total - pro_gov
    pro_gov_pct = (pro_gov / total) * 100
    ind_pct = (independent / total) * 100

    if ind_pct > 66:
        return BlindspotInfo(
            type="pro_gov_blindspot",
            pro_gov_coverage_pct=pro_gov_pct,
            independent_coverage_pct=ind_pct,
            description_en="Pro-government media is underreporting this story",
            description_hu="A kormánypárti média alulreprezentálja ezt a hírt",
        )
    elif pro_gov_pct > 66:
        return BlindspotInfo(
            type="independent_blindspot",
            pro_gov_coverage_pct=pro_gov_pct,
            independent_coverage_pct=ind_pct,
            description_en="Independent media is underreporting this story",
            description_hu="A független média alulreprezentálja ezt a hírt",
        )
    return BlindspotInfo(
        type="both_sides",
        pro_gov_coverage_pct=pro_gov_pct,
        independent_coverage_pct=ind_pct,
        description_en="This story is covered across the spectrum",
        description_hu="Ezt a hírt a teljes spektrum lefedi",
    )


def enrich_story(story: StoryCluster) -> StoryCluster:
    """Full enrichment pipeline for a single story."""
    story = summarize_story(story)
    story = translate_articles(story)
    story.bias_distribution = compute_bias_distribution(story)
    story.blindspot = compute_blindspot(story.bias_distribution)

    # Pick best image (prefer higher-factuality outlets)
    outlets = _load_outlets()
    factuality_order = ["very_high", "high", "mixed", "low", "very_low"]
    best_image = None
    best_rank = len(factuality_order)
    for a in story.articles:
        if a.image_url:
            outlet = outlets.get(a.outlet_id, {})
            fact = outlet.get("factuality", "mixed")
            rank = factuality_order.index(fact) if fact in factuality_order else 3
            if rank < best_rank:
                best_rank = rank
                best_image = a.image_url
    if best_image:
        story.image_url = best_image

    return story


def _auto_tag_topics(story: StoryCluster) -> list[str]:
    """Fallback: tag topics by keyword matching when Claude fails."""
    text = " ".join([
        story.title_en, story.title_hu,
        story.ai_summary_en, story.ai_summary_hu,
    ] + [a.headline_hu + " " + a.summary_hu for a in story.articles[:5]]).lower()

    tags = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(topic)
    return tags[:3]  # Max 3 tags
