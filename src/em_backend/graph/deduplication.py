"""Argument deduplication via semantic similarity + LLM judgment."""

from __future__ import annotations

import json
import os
from typing import Optional

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class DedupResult(BaseModel):
    action: str  # "skip" | "insert_new" | "insert_linked"
    existing_argument_id: Optional[str] = None
    existing_text: Optional[str] = None
    similarity_score: float = 0.0
    llm_judgment: Optional[str] = None  # "same_claim" | "related" | "different"
    explanation: str = ""


async def check_duplicate(
    claim_text: str,
    party: Optional[str] = None,
    similarity_threshold: float = 0.85,
    llm_threshold: float = 0.70,
) -> DedupResult:
    """Check if a claim already exists in the graph.

    Args:
        claim_text: The new argument text.
        party: Optional party filter.
        similarity_threshold: Cosine similarity above which to invoke LLM.
        llm_threshold: Cosine similarity above which to check at all.

    Returns:
        DedupResult with action to take.
    """
    logger.info("dedup_check_start", claim=claim_text[:80], party=party)

    from em_backend.graph.embeddings import find_similar_to_text

    similar = find_similar_to_text(claim_text, limit=5, min_similarity=llm_threshold)

    if not similar:
        logger.info("dedup_no_match", claim=claim_text[:80])
        return DedupResult(action="insert_new", similarity_score=0.0)

    top_match = similar[0]
    score = top_match["similarity"]

    logger.info("dedup_top_match",
        claim=claim_text[:80],
        match=top_match["text"][:80],
        similarity=round(score, 3))

    if score < similarity_threshold:
        return DedupResult(
            action="insert_new",
            similarity_score=score,
            existing_argument_id=top_match.get("argument_id"),
            existing_text=top_match["text"],
        )

    # LLM judgment for high-similarity matches
    judgment = await _llm_judge_duplicate(claim_text, top_match["text"])

    logger.info("dedup_llm_judgment",
        judgment=judgment,
        claim=claim_text[:60],
        match=top_match["text"][:60])

    if judgment["judgment"] == "same_claim":
        return DedupResult(
            action="skip",
            existing_argument_id=top_match.get("argument_id"),
            existing_text=top_match["text"],
            similarity_score=score,
            llm_judgment="same_claim",
            explanation=judgment.get("explanation", ""),
        )
    elif judgment["judgment"] == "related":
        return DedupResult(
            action="insert_linked",
            existing_argument_id=top_match.get("argument_id"),
            existing_text=top_match["text"],
            similarity_score=score,
            llm_judgment="related",
            explanation=judgment.get("explanation", ""),
        )
    else:
        return DedupResult(
            action="insert_new",
            similarity_score=score,
            llm_judgment="different",
            explanation=judgment.get("explanation", ""),
        )


async def _llm_judge_duplicate(new_text: str, existing_text: str) -> dict:
    """Ask Gemini whether two arguments are the same claim."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = f"""You compare two political arguments and determine their relationship.
Respond in JSON: {{"judgment": "same_claim"|"related"|"different", "explanation": "..."}}

- "same_claim": They express the exact same political position, just worded differently.
- "related": They are about the same topic and direction, but make distinct points.
- "different": They are about different topics or take opposing positions.

Argument A: {new_text}

Argument B: {existing_text}"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
            max_output_tokens=200,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    import re
    text = response.text or '{"judgment": "different"}'
    if text.strip().startswith("```"):
        match = re.search(r'\{[^}]+\}', text)
        if match:
            text = match.group()
    return json.loads(text)
