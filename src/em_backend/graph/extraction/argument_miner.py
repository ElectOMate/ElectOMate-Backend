"""LLM-based argument extraction from political text.

Uses OpenAI GPT-4o to extract structured arguments from Hungarian
political content (speeches, manifestos, interviews, articles).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from em_backend.core.config import settings
from em_backend.graph.connectors.base import IngestedDocument

logger = structlog.get_logger(__name__)


# ============================================================================
# Pydantic models for extracted arguments
# ============================================================================


class ExtractedArgument(BaseModel):
    """A single argument extracted from political text."""

    claim: str = Field(description="The main assertion being made")
    premises: list[str] = Field(
        default_factory=list,
        description="Supporting reasons for the claim",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Specific data, quotes, or references cited",
    )
    conclusion: str = Field(
        default="",
        description="What the speaker wants the audience to believe or do",
    )
    argument_type: str = Field(
        default="policy",
        description="Type: policy, value, fact, or causal",
    )
    topic_tags: list[str] = Field(
        default_factory=list,
        description="Topic categories this argument relates to",
    )
    speaker: str | None = Field(
        default=None,
        description="Name of the speaker if identifiable",
    )
    party: str | None = Field(
        default=None,
        description="Party affiliation if identifiable",
    )
    sentiment: str = Field(
        default="neutral",
        description="Stance: for, against, or neutral",
    )
    strength: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Argument strength rating 1-5",
    )
    rebuts: str | None = Field(
        default=None,
        description="Description of opposing argument if this is a rebuttal",
    )
    source_context: str = Field(
        default="",
        description="Brief context of where this argument appears",
    )


class ExtractionResult(BaseModel):
    """Result of argument extraction from a document."""

    arguments: list[ExtractedArgument]
    source_title: str
    source_type: str
    extraction_date: date
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall extraction confidence",
    )
    warnings: list[str] = Field(default_factory=list)


# ============================================================================
# Extraction prompts
# ============================================================================

SYSTEM_PROMPT = """You are an expert political analyst specializing in Hungarian politics.
Your task is to extract ALL political arguments from the provided text.

You must identify:
1. Claims — explicit assertions or policy positions
2. Premises — reasoning that supports claims
3. Evidence — data, statistics, quotes, or references
4. Rebuttals — arguments that counter other arguments
5. Topic classification — categorize each argument

IMPORTANT RULES:
- Extract arguments in their ORIGINAL language (Hungarian)
- Be comprehensive — extract every distinct argument, not just the main ones
- Each argument should be self-contained (understandable without context)
- Identify speakers and party affiliations when possible
- Rate argument strength based on how well-supported it is (1=bare assertion, 5=well-evidenced)
- Classify sentiment as "for" (supporting a position), "against" (opposing), or "neutral" (descriptive)

Use these topic categories (in Hungarian):
- Gazdaság (Economy)
- EU-kapcsolatok (EU Relations)
- Migráció (Migration)
- Egészségügy (Healthcare)
- Oktatás (Education)
- Honvédelem (Defense)
- Szociálpolitika (Social Policy)
- Sajtószabadság (Press Freedom)
- Korrupció (Corruption)
- Jogállamiság (Rule of Law)
- Energia (Energy)
- Környezetvédelem (Environment)
- Ukrajna-háború (Ukraine War)
- Lakhatás (Housing)
- Other (specify)"""

EXTRACTION_PROMPT = """Analyze the following Hungarian political text and extract ALL arguments.

For each argument, provide a JSON object with these fields:
- claim: The main assertion (in Hungarian)
- premises: List of supporting reasons (in Hungarian)
- evidence: List of specific data/quotes cited (in Hungarian)
- conclusion: What the speaker wants the audience to believe/do (in Hungarian)
- argument_type: "policy" | "value" | "fact" | "causal"
- topic_tags: List of topic categories from the system prompt
- speaker: Speaker name if identifiable (or null)
- party: Party name/shortname if identifiable (or null)
- sentiment: "for" | "against" | "neutral"
- strength: 1-5 rating
- rebuts: Description of opposing argument if this is a rebuttal (or null)
- source_context: Brief description of where in the text this appears

Return a JSON array of argument objects. Return at least 1 argument if any political content exists.
If the text contains no political arguments, return an empty array.

TEXT:
{text}"""


# ============================================================================
# Extraction functions
# ============================================================================


async def extract_arguments(
    text: str,
    source_title: str = "",
    source_type: str = "unknown",
    max_tokens: int = 4096,
) -> ExtractionResult:
    """Extract political arguments from a text using GPT-4o.

    Args:
        text: The text to analyze.
        source_title: Title of the source document.
        source_type: Type of source (manifesto, speech, etc.).
        max_tokens: Max response tokens for the LLM.

    Returns:
        ExtractionResult with extracted arguments.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Truncate very long texts to fit context window
    max_input_chars = 30_000
    truncated = len(text) > max_input_chars
    if truncated:
        text = text[:max_input_chars]
        logger.warning(
            "Truncated input text",
            original_length=len(text),
            max_chars=max_input_chars,
        )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.1,  # Low temperature for consistent extraction
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        # Handle both {"arguments": [...]} and direct array formats
        if isinstance(parsed, list):
            arg_dicts = parsed
        elif isinstance(parsed, dict) and "arguments" in parsed:
            arg_dicts = parsed["arguments"]
        else:
            arg_dicts = [parsed] if parsed else []

        arguments = []
        for arg_dict in arg_dicts:
            try:
                arguments.append(ExtractedArgument(**arg_dict))
            except Exception as e:
                logger.warning(
                    "Failed to parse argument",
                    error=str(e),
                    arg_dict=arg_dict,
                )

        warnings = []
        if truncated:
            warnings.append("Input text was truncated")
        if not arguments:
            warnings.append("No arguments extracted")

        # Estimate confidence based on extraction quality signals
        confidence = _estimate_confidence(arguments, text)

        return ExtractionResult(
            arguments=arguments,
            source_title=source_title,
            source_type=source_type,
            extraction_date=date.today(),
            confidence=confidence,
            warnings=warnings,
        )

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON", error=str(e))
        return ExtractionResult(
            arguments=[],
            source_title=source_title,
            source_type=source_type,
            extraction_date=date.today(),
            confidence=0.0,
            warnings=[f"JSON parse error: {e}"],
        )
    except Exception as e:
        logger.error("Argument extraction failed", error=str(e))
        return ExtractionResult(
            arguments=[],
            source_title=source_title,
            source_type=source_type,
            extraction_date=date.today(),
            confidence=0.0,
            warnings=[f"Extraction error: {e}"],
        )


async def extract_arguments_from_document(
    doc: IngestedDocument,
) -> ExtractionResult:
    """Extract arguments from an IngestedDocument.

    Processes the document's segments or full text.
    For long documents, processes in chunks and merges results.
    """
    text = doc.full_text
    if not text.strip():
        logger.warning("Empty document", title=doc.title)
        return ExtractionResult(
            arguments=[],
            source_title=doc.title,
            source_type=doc.source_type,
            extraction_date=date.today(),
            warnings=["Empty document"],
        )

    # For short texts, extract directly
    if len(text) <= 30_000:
        return await extract_arguments(
            text=text,
            source_title=doc.title,
            source_type=doc.source_type,
        )

    # For long texts, chunk and merge
    logger.info(
        "Chunking long document for extraction",
        title=doc.title,
        text_length=len(text),
    )

    chunk_size = 25_000
    overlap = 2_000
    all_arguments: list[ExtractedArgument] = []
    all_warnings: list[str] = []

    pos = 0
    chunk_idx = 0
    while pos < len(text):
        chunk = text[pos : pos + chunk_size]
        result = await extract_arguments(
            text=chunk,
            source_title=f"{doc.title} (chunk {chunk_idx})",
            source_type=doc.source_type,
        )
        all_arguments.extend(result.arguments)
        all_warnings.extend(result.warnings)
        pos += chunk_size - overlap
        chunk_idx += 1

    # Deduplicate arguments with similar claims
    deduped = _deduplicate_arguments(all_arguments)

    return ExtractionResult(
        arguments=deduped,
        source_title=doc.title,
        source_type=doc.source_type,
        extraction_date=date.today(),
        confidence=_estimate_confidence(deduped, text),
        warnings=all_warnings,
    )


async def batch_extract(
    documents: list[IngestedDocument],
    concurrency: int = 3,
) -> list[ExtractionResult]:
    """Extract arguments from multiple documents with concurrency control.

    Args:
        documents: List of documents to process.
        concurrency: Max concurrent extraction tasks.

    Returns:
        List of ExtractionResults.
    """
    import asyncio

    semaphore = asyncio.Semaphore(concurrency)

    async def _extract_with_semaphore(doc: IngestedDocument) -> ExtractionResult:
        async with semaphore:
            logger.info("Extracting arguments", title=doc.title)
            return await extract_arguments_from_document(doc)

    tasks = [_extract_with_semaphore(doc) for doc in documents]
    return await asyncio.gather(*tasks)


# ============================================================================
# Helper functions
# ============================================================================


def _estimate_confidence(
    arguments: list[ExtractedArgument],
    source_text: str,
) -> float:
    """Estimate extraction confidence based on quality signals."""
    if not arguments:
        return 0.0

    signals = []

    # Signal: arguments found relative to text length
    expected_args = max(1, len(source_text) / 3000)
    ratio = len(arguments) / expected_args
    signals.append(min(1.0, ratio))

    # Signal: arguments have premises (not just bare claims)
    with_premises = sum(1 for a in arguments if a.premises)
    signals.append(with_premises / len(arguments) if arguments else 0)

    # Signal: arguments have topic tags
    with_topics = sum(1 for a in arguments if a.topic_tags)
    signals.append(with_topics / len(arguments) if arguments else 0)

    # Signal: speaker/party attribution
    with_attribution = sum(
        1 for a in arguments if a.speaker or a.party
    )
    signals.append(with_attribution / len(arguments) if arguments else 0)

    return sum(signals) / len(signals)


def _deduplicate_arguments(
    arguments: list[ExtractedArgument],
    similarity_threshold: float = 0.85,
) -> list[ExtractedArgument]:
    """Remove near-duplicate arguments based on claim text similarity.

    Uses simple character-level overlap for speed. For production,
    consider using embeddings from Weaviate.
    """
    if len(arguments) <= 1:
        return arguments

    kept: list[ExtractedArgument] = []
    for arg in arguments:
        is_duplicate = False
        for existing in kept:
            similarity = _text_similarity(arg.claim, existing.claim)
            if similarity >= similarity_threshold:
                is_duplicate = True
                # Merge: keep the one with more premises/evidence
                if len(arg.premises) > len(existing.premises):
                    kept.remove(existing)
                    kept.append(arg)
                break
        if not is_duplicate:
            kept.append(arg)

    if len(kept) < len(arguments):
        logger.info(
            "Deduplicated arguments",
            original=len(arguments),
            kept=len(kept),
        )

    return kept


def _text_similarity(a: str, b: str) -> float:
    """Simple character-level Jaccard similarity between two strings."""
    if not a or not b:
        return 0.0
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0
