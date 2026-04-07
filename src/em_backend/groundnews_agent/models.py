"""Pydantic models for the Ground News agent pipeline."""
from __future__ import annotations
from pydantic import BaseModel, Field


class FetchedArticle(BaseModel):
    """Raw article from RSS + newspaper4k extraction."""
    outlet_id: str
    title: str
    url: str
    summary: str = ""
    full_text: str = ""
    image_url: str | None = None
    published: str = ""
    language: str = "hu"


class StoryArticle(BaseModel):
    """An article within a story cluster, ready for frontend."""
    outlet_id: str
    headline_en: str
    headline_hu: str
    summary_en: str
    summary_hu: str
    url: str
    image_url: str | None = None
    date: str
    stance: str = "neutral"


class BlindspotInfo(BaseModel):
    type: str = "both_sides"
    pro_gov_coverage_pct: float = 50.0
    independent_coverage_pct: float = 50.0
    description_en: str = ""
    description_hu: str = ""


class StoryCluster(BaseModel):
    """A single news story aggregated from multiple outlets."""
    id: str
    title_en: str
    title_hu: str
    ai_summary_en: str = ""
    ai_summary_hu: str = ""
    image_url: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    articles: list[StoryArticle] = Field(default_factory=list)
    bias_distribution: dict[str, int] = Field(default_factory=dict)
    blindspot: BlindspotInfo = Field(default_factory=BlindspotInfo)
    importance_score: int = 5
    first_seen: str = ""
    last_updated: str = ""
    source_count: int = 0


class StoriesOutput(BaseModel):
    """Top-level output written to stories.json."""
    generated_at: str = ""
    story_count: int = 0
    stories: list[StoryCluster] = Field(default_factory=list)


# ── Claude structured output models ──

class ClaudeStoryMeta(BaseModel):
    """Claude generates this for each story cluster."""
    title_en: str
    title_hu: str
    summary_en: str = Field(description="Neutral 2-3 sentence summary synthesizing all perspectives")
    summary_hu: str = Field(description="Same summary in Hungarian")
    topic_tags: list[str] = Field(description="Which of the 10 election topics this relates to")
    importance_score: int = Field(ge=1, le=10, description="1-10 importance for Hungarian 2026 election")


class ClaudeArticleTranslation(BaseModel):
    """Claude translates and analyzes a single article."""
    headline_en: str
    headline_hu: str
    summary_en: str
    summary_hu: str
    stance: str = Field(description="for, against, neutral, or mixed")


class ClaudeArticleBatch(BaseModel):
    """Batch of article translations."""
    articles: list[ClaudeArticleTranslation]
