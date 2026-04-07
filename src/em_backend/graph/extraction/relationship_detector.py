"""Argument relationship detection.

Determines logical relationships between extracted arguments:
SUPPORTS, REBUTS, CONTRADICTS, or UNRELATED.
"""

from __future__ import annotations

import json
import os
from enum import StrEnum

import structlog
from google import genai
from google.genai import types

from em_backend.graph.extraction.argument_miner import ExtractedArgument

logger = structlog.get_logger(__name__)


class ArgumentRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    REBUTS = "REBUTS"
    CONTRADICTS = "CONTRADICTS"
    UNRELATED = "UNRELATED"


class RelationResult:
    """Result of relationship detection between two arguments."""

    def __init__(
        self,
        relation: ArgumentRelation,
        confidence: float,
        explanation: str = "",
    ) -> None:
        self.relation = relation
        self.confidence = confidence
        self.explanation = explanation


RELATION_PROMPT = """Analyze the logical relationship between these two Hungarian political arguments.

ARGUMENT A:
Claim: {claim_a}
Premises: {premises_a}
Party: {party_a}

ARGUMENT B:
Claim: {claim_b}
Premises: {premises_b}
Party: {party_b}

Determine the relationship from A to B:
- SUPPORTS: A provides evidence or reasoning that strengthens B
- REBUTS: A directly counters or argues against B
- CONTRADICTS: A and B make incompatible claims on the same topic
- UNRELATED: A and B are about different topics or have no logical connection

Return JSON:
{{"relation": "SUPPORTS|REBUTS|CONTRADICTS|UNRELATED", "confidence": 0.0-1.0, "explanation": "Brief explanation"}}"""


async def detect_relationship(
    arg_a: ExtractedArgument,
    arg_b: ExtractedArgument,
) -> RelationResult:
    """Detect the logical relationship between two arguments using LLM.

    Args:
        arg_a: First argument.
        arg_b: Second argument.

    Returns:
        RelationResult with relation type, confidence, and explanation.
    """
    # Quick heuristic: same topic check
    common_topics = set(arg_a.topic_tags) & set(arg_b.topic_tags)
    if not common_topics:
        # Different topics are likely unrelated
        return RelationResult(
            relation=ArgumentRelation.UNRELATED,
            confidence=0.6,
            explanation="No common topic tags",
        )

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = RELATION_PROMPT.format(
        claim_a=arg_a.claim,
        premises_a=", ".join(arg_a.premises) or "N/A",
        party_a=arg_a.party or "Unknown",
        claim_b=arg_b.claim,
        premises_b=", ".join(arg_b.premises) or "N/A",
        party_b=arg_b.party or "Unknown",
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=200,
            ),
        )

        content = response.text or "{}"
        parsed = json.loads(content)

        relation_str = parsed.get("relation", "UNRELATED")
        try:
            relation = ArgumentRelation(relation_str)
        except ValueError:
            relation = ArgumentRelation.UNRELATED

        return RelationResult(
            relation=relation,
            confidence=float(parsed.get("confidence", 0.5)),
            explanation=parsed.get("explanation", ""),
        )

    except Exception as e:
        logger.warning("Relationship detection failed", error=str(e))
        return RelationResult(
            relation=ArgumentRelation.UNRELATED,
            confidence=0.0,
            explanation=f"Detection failed: {e}",
        )


async def detect_relationships_batch(
    arguments: list[ExtractedArgument],
    same_topic_only: bool = True,
    min_confidence: float = 0.5,
) -> list[tuple[int, int, RelationResult]]:
    """Detect relationships between all pairs of arguments.

    Args:
        arguments: List of arguments to compare.
        same_topic_only: Only compare arguments sharing a topic tag.
        min_confidence: Minimum confidence to include a relationship.

    Returns:
        List of (idx_a, idx_b, RelationResult) tuples.
    """
    import asyncio

    pairs: list[tuple[int, int]] = []
    for i in range(len(arguments)):
        for j in range(i + 1, len(arguments)):
            if same_topic_only:
                topics_i = set(arguments[i].topic_tags)
                topics_j = set(arguments[j].topic_tags)
                if not topics_i & topics_j:
                    continue
            pairs.append((i, j))

    logger.info(
        "Detecting relationships",
        total_arguments=len(arguments),
        pairs_to_check=len(pairs),
    )

    results: list[tuple[int, int, RelationResult]] = []

    # Process in batches to respect rate limits
    batch_size = 5
    for batch_start in range(0, len(pairs), batch_size):
        batch = pairs[batch_start : batch_start + batch_size]
        tasks = [
            detect_relationship(arguments[i], arguments[j])
            for i, j in batch
        ]
        batch_results = await asyncio.gather(*tasks)

        for (i, j), result in zip(batch, batch_results):
            if (
                result.relation != ArgumentRelation.UNRELATED
                and result.confidence >= min_confidence
            ):
                results.append((i, j, result))

    logger.info(
        "Relationship detection complete",
        relationships_found=len(results),
    )
    return results
