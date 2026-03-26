"""Topic taxonomy builder for Hungarian political arguments.

Uses LLM-assisted classification to map extracted arguments
to the predefined topic hierarchy, with support for discovering
new subtopics dynamically.
"""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI

from em_backend.core.config import settings
from em_backend.graph.extraction.argument_miner import ExtractedArgument
from em_backend.graph.schema import SEED_TOPICS

logger = structlog.get_logger(__name__)

# Build topic lookup from seed data
TOPIC_KEYWORDS: dict[str, list[str]] = {
    topic["name"]: topic["keywords"] for topic in SEED_TOPICS
}

TOPIC_NAME_EN: dict[str, str] = {
    topic["name"]: topic["name_en"] for topic in SEED_TOPICS
}

ALL_TOPIC_NAMES = list(TOPIC_KEYWORDS.keys())


def classify_topic_by_keywords(text: str) -> list[str]:
    """Classify text into topics using keyword matching.

    Fast, no API call needed. Good for initial filtering.

    Args:
        text: Text to classify.

    Returns:
        List of matching topic names (Hungarian).
    """
    text_lower = text.lower()
    matches = []

    for topic_name, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches.append(topic_name)
                break

    return matches


async def classify_topic_by_llm(
    argument: ExtractedArgument,
) -> list[str]:
    """Classify an argument into topics using LLM.

    More accurate than keyword matching, handles context and nuance.

    Args:
        argument: The extracted argument to classify.

    Returns:
        List of topic names (Hungarian).
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    topic_list = "\n".join(
        f"- {name} ({TOPIC_NAME_EN.get(name, '')})"
        for name in ALL_TOPIC_NAMES
    )

    prompt = f"""Classify the following Hungarian political argument into one or more topics.

Available topics:
{topic_list}

Argument:
Claim: {argument.claim}
Premises: {', '.join(argument.premises)}
Context: {argument.source_context}

Return a JSON object with:
{{"topics": ["Topic1", "Topic2"]}}

Only use topic names from the list above. Return 1-3 most relevant topics."""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=200,
            temperature=0.0,
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        topics = parsed.get("topics", [])

        # Validate against known topics
        valid_topics = [t for t in topics if t in ALL_TOPIC_NAMES]

        if not valid_topics and topics:
            logger.warning(
                "LLM returned unknown topics, falling back to keywords",
                returned_topics=topics,
            )
            return classify_topic_by_keywords(argument.claim)

        return valid_topics

    except Exception as e:
        logger.warning("LLM topic classification failed, using keywords", error=str(e))
        return classify_topic_by_keywords(argument.claim)


async def classify_arguments_batch(
    arguments: list[ExtractedArgument],
    use_llm: bool = True,
) -> dict[int, list[str]]:
    """Classify a batch of arguments into topics.

    Args:
        arguments: List of arguments to classify.
        use_llm: Whether to use LLM classification (slower but more accurate).

    Returns:
        Dict mapping argument index to list of topic names.
    """
    results: dict[int, list[str]] = {}

    for i, arg in enumerate(arguments):
        # First try keyword matching (fast)
        keyword_topics = classify_topic_by_keywords(arg.claim)

        if keyword_topics and not use_llm:
            results[i] = keyword_topics
        elif use_llm:
            # Use LLM for more accurate classification
            llm_topics = await classify_topic_by_llm(arg)
            results[i] = llm_topics if llm_topics else keyword_topics
        else:
            results[i] = keyword_topics

        # Also use the argument's own topic_tags if available
        if arg.topic_tags:
            existing = set(results.get(i, []))
            for tag in arg.topic_tags:
                # Try to map to our canonical topics
                mapped = _map_tag_to_topic(tag)
                if mapped:
                    existing.add(mapped)
            results[i] = list(existing)

    return results


def _map_tag_to_topic(tag: str) -> str | None:
    """Map a free-form topic tag to a canonical topic name."""
    tag_lower = tag.lower()

    # Check if tag directly matches a topic name
    for topic_name in ALL_TOPIC_NAMES:
        if topic_name.lower() == tag_lower:
            return topic_name

    # Check against English names
    for hu_name, en_name in TOPIC_NAME_EN.items():
        if en_name.lower() == tag_lower:
            return hu_name

    # Check against keywords
    for topic_name, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() == tag_lower or tag_lower in kw.lower():
                return topic_name

    return None
