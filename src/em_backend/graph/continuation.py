"""Generate continuation arguments for new knowledge graph nodes."""

from __future__ import annotations

import json
import os
from typing import Optional

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ContinuationArgument(BaseModel):
    claim: str  # max 280 chars
    continuation_type: str  # "reason" | "consequence" | "related_position"
    rationale: str  # why this follows from the parent


class ContinuationResult(BaseModel):
    parent_claim: str
    continuations: list[ContinuationArgument]
    generated_count: int
    inserted_count: int
    skipped_duplicate_count: int


async def generate_continuations(
    parent_claim: str,
    parent_party: Optional[str] = None,
    parent_topic: Optional[str] = None,
    min_count: int = 2,
    max_count: int = 5,
) -> list[ContinuationArgument]:
    """Generate continuation arguments for a parent claim."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    context = f"Party: {parent_party}" if parent_party else ""
    if parent_topic:
        context += f", Topic: {parent_topic}"

    prompt = f"""You are a Hungarian political analyst. Given a political argument,
generate {min_count}-{max_count} continuation arguments in Hungarian.

Each continuation should be ONE of:
- "reason": Why someone would believe this claim
- "consequence": What follows if this is true or acted upon
- "related_position": An adjacent political position that logically connects

Rules:
- Each claim must be max 280 characters in Hungarian
- Each must be a distinct, concrete claim (not vague)
- Generate fewer if the topic doesn't warrant more
- Stay politically neutral

Respond in JSON: {{"continuations": [{{"claim": "...", "type": "reason|consequence|related_position", "rationale": "..."}}]}}

Parent argument: {parent_claim}
{context}"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
            max_output_tokens=2000,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    import re
    try:
        text = response.text or '{"continuations": []}'
        if text.strip().startswith("```"):
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group()
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("continuation_json_parse_error", text=response.text[:200] if response.text else "")
        data = {"continuations": []}

    continuations = []
    for c in data.get("continuations", [])[:max_count]:
        continuations.append(ContinuationArgument(
            claim=c["claim"][:280],
            continuation_type=c.get("type", "related_position"),
            rationale=c.get("rationale", ""),
        ))

    logger.info("continuations_generated",
        parent=parent_claim[:80],
        count=len(continuations),
        types=[c.continuation_type for c in continuations])

    return continuations


async def generate_and_insert_continuations(
    parent_claim: str,
    parent_party: Optional[str] = None,
    parent_topic: Optional[str] = None,
    graph=None,
) -> ContinuationResult:
    """Generate continuations, deduplicate, and insert into graph."""
    from em_backend.graph.db import get_graph_db
    from em_backend.graph.deduplication import check_duplicate
    from em_backend.graph.embeddings import embed_text, store_embedding

    if graph is None:
        graph = get_graph_db()

    continuations = await generate_continuations(
        parent_claim, parent_party, parent_topic
    )

    inserted = 0
    skipped = 0
    _escape = lambda s: s.replace("'", "\\'") if s else ""

    for cont in continuations:
        dedup = await check_duplicate(cont.claim, party=parent_party)

        if dedup.action == "skip":
            logger.info("continuation_skipped", claim=cont.claim[:80], reason="duplicate")
            skipped += 1
            continue

        claim_escaped = _escape(cont.claim)

        graph.write(f"""
            MERGE (a:Argument {{text: '{claim_escaped}'}})
            SET a.generated = true,
                a.continuation_type = '{cont.continuation_type}',
                a.rationale = '{_escape(cont.rationale)[:200]}',
                a.argument_type = 'generated'
            RETURN a
        """)

        # Link to parent
        parent_escaped = _escape(parent_claim)
        graph.write(f"""
            MATCH (parent:Argument {{text: '{parent_escaped}'}})
            MATCH (child:Argument {{text: '{claim_escaped}'}})
            MERGE (parent)-[:CONTINUES]->(child)
        """)

        # Link to party
        if parent_party:
            try:
                graph.write(f"""
                    MATCH (a:Argument {{text: '{claim_escaped}'}})
                    MATCH (p:Party {{shortname: '{parent_party}'}})
                    MERGE (a)-[:MADE_BY]->(p)
                """)
            except Exception:
                pass

        # Link to topic
        if parent_topic:
            try:
                graph.write(f"""
                    MATCH (a:Argument {{text: '{claim_escaped}'}})
                    MATCH (t:Topic {{name: '{_escape(parent_topic)}'}})
                    MERGE (a)-[:ABOUT]->(t)
                """)
            except Exception:
                pass

        # Embed
        try:
            embedding = embed_text(cont.claim)
            store_embedding(
                argument_id=f"gen::{cont.claim[:80]}",
                text=cont.claim,
                embedding=embedding,
                party=parent_party,
            )
        except Exception as e:
            logger.warning("continuation_embed_failed", error=str(e))

        if dedup.action == "insert_linked" and dedup.existing_text:
            try:
                graph.write(f"""
                    MATCH (a1:Argument {{text: '{claim_escaped}'}})
                    MATCH (a2:Argument {{text: '{_escape(dedup.existing_text)}'}})
                    MERGE (a1)-[:EQUIVALENT]->(a2)
                """)
            except Exception:
                pass

        inserted += 1
        logger.info("continuation_inserted",
            claim=cont.claim[:80],
            type=cont.continuation_type)

    result = ContinuationResult(
        parent_claim=parent_claim,
        continuations=continuations,
        generated_count=len(continuations),
        inserted_count=inserted,
        skipped_duplicate_count=skipped,
    )

    logger.info("continuations_complete",
        parent=parent_claim[:80],
        generated=result.generated_count,
        inserted=result.inserted_count,
        skipped=result.skipped_duplicate_count)

    return result
