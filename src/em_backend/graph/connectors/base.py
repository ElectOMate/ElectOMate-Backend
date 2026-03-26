"""Base models for all data source connectors."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    MANIFESTO = "manifesto"
    SPEECH = "speech"
    INTERVIEW = "interview"
    LAW = "law"
    DOCUMENT = "document"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    PRESS_RELEASE = "press_release"


class Modality(StrEnum):
    TEXT = "text"
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    HTML = "html"
    XML = "xml"


class SpeakerInfo(BaseModel):
    name: str
    party: str | None = None
    role: str | None = None  # e.g., "Prime Minister", "MP", "Party Leader"
    party_at_time: str | None = None  # party affiliation at time of speech


class TextSegment(BaseModel):
    text: str
    speaker: str | None = None
    timestamp: str | None = None  # MM:SS for video, None for text
    page_number: int | None = None  # for PDFs
    paragraph_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestedDocument(BaseModel):
    """Standardized output from all data source connectors."""

    source_type: SourceType
    modality: Modality
    source_url: str | None = None
    source_path: str | None = None  # local file path if applicable
    title: str
    date: date | None = None
    language: str = "hu"  # ISO 639-1
    speakers: list[SpeakerInfo] = Field(default_factory=list)
    segments: list[TextSegment] = Field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenate all segments into a single text."""
        if self.raw_text:
            return self.raw_text
        return "\n\n".join(seg.text for seg in self.segments)

    @property
    def speaker_names(self) -> list[str]:
        """Get unique speaker names from segments."""
        return list({seg.speaker for seg in self.segments if seg.speaker})
