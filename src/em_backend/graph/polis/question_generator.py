"""Pol.is follow-up question generator.

Generates targeted follow-up questions based on the argument knowledge graph
to help users clarify WHY they agree or disagree with a statement.
"""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from em_backend.core.config import settings
from em_backend.graph.db import GraphDB, get_graph_db

logger = structlog.get_logger(__name__)


class PolisFollowUp(BaseModel):
    """A follow-up question for Pol.is deliberation."""

    text: str = Field(description="The follow-up statement/question text")
    question_type: str = Field(
        description="Type: clarifying, probing, contrasting, or deepening"
    )
    source_argument: str | None = Field(
        default=None,
        description="The argument this follow-up is derived from",
    )
    rationale: str = Field(
        default="",
        description="Why this follow-up is relevant",
    )
    priority: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Priority 1=highest, 5=lowest",
    )


class FollowUpResult(BaseModel):
    """Result of follow-up question generation."""

    original_statement: str
    user_vote: str  # "agree", "disagree", "pass"
    follow_ups: list[PolisFollowUp]


GENERATION_PROMPT = """You are generating follow-up statements for a Pol.is deliberation platform about Hungarian politics.

A user has {vote_description} the following statement:
"{statement}"

Based on the related arguments from the knowledge graph below, generate follow-up statements
that help the user clarify WHY they {vote_verb}.

RELATED ARGUMENTS FROM THE GRAPH:
{related_arguments}

REBUTTING ARGUMENTS:
{rebuttals}

Generate 3-5 follow-up statements of these types:
1. CLARIFYING: "You {vote_verb_past} that [X]. Is this because [premise A] or [premise B]?"
2. PROBING: Dig deeper into the reasoning behind their vote
3. CONTRASTING: Present an opposing view to test conviction: "Would you still {vote_verb} if [counter-argument]?"
4. DEEPENING: Ask about specific implications: "If [claim], then should [policy consequence]?"

RULES:
- Write in Hungarian (magyar nyelven)
- Each statement should be a clear, voteable Pol.is statement (agree/disagree format)
- Keep statements concise (max 140 characters ideal, 280 max)
- Don't repeat the original statement
- Make each follow-up genuinely useful for understanding opinion clusters

Return JSON:
{{
  "follow_ups": [
    {{
      "text": "Hungarian statement text",
      "question_type": "clarifying|probing|contrasting|deepening",
      "source_argument": "The argument this derives from (or null)",
      "rationale": "Why this follow-up is informative",
      "priority": 1-5
    }}
  ]
}}"""


async def generate_followups(
    statement: str,
    user_vote: str,
    graph: GraphDB | None = None,
    max_followups: int = 5,
) -> FollowUpResult:
    """Generate Pol.is follow-up questions based on the argument graph.

    Args:
        statement: The original Pol.is statement the user voted on.
        user_vote: "agree", "disagree", or "pass".
        graph: GraphDB instance.
        max_followups: Maximum number of follow-ups to generate.

    Returns:
        FollowUpResult with generated follow-up questions.
    """
    if graph is None:
        graph = get_graph_db()

    # Find related arguments in the graph
    escaped_statement = statement.replace("'", "\\'")

    # Search for arguments with similar text
    related_args = _find_related_arguments(graph, statement)
    rebuttals = _find_rebuttals(graph, statement)

    # Format for LLM
    vote_description = {
        "agree": "AGREED with",
        "disagree": "DISAGREED with",
        "pass": "PASSED on",
    }.get(user_vote, "voted on")

    vote_verb = {
        "agree": "agree",
        "disagree": "disagree",
        "pass": "have no opinion on",
    }.get(user_vote, "voted on")

    vote_verb_past = {
        "agree": "agreed",
        "disagree": "disagreed",
        "pass": "passed on",
    }.get(user_vote, "voted on")

    related_text = "\n".join(
        f"- [{a.get('party', '?')}] {a.get('text', '')}"
        for a in related_args
    ) or "No directly related arguments found in the graph."

    rebuttal_text = "\n".join(
        f"- [{a.get('party', '?')}] {a.get('text', '')}"
        for a in rebuttals
    ) or "No rebuttals found."

    prompt = GENERATION_PROMPT.format(
        vote_description=vote_description,
        statement=statement,
        vote_verb=vote_verb,
        vote_verb_past=vote_verb_past,
        related_arguments=related_text,
        rebuttals=rebuttal_text,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.7,  # Some creativity for diverse questions
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        follow_ups = []
        for fu_dict in parsed.get("follow_ups", [])[:max_followups]:
            try:
                follow_ups.append(PolisFollowUp(**fu_dict))
            except Exception as e:
                logger.warning("Failed to parse follow-up", error=str(e))

        return FollowUpResult(
            original_statement=statement,
            user_vote=user_vote,
            follow_ups=follow_ups,
        )

    except Exception as e:
        logger.error("Follow-up generation failed", error=str(e))
        return FollowUpResult(
            original_statement=statement,
            user_vote=user_vote,
            follow_ups=[],
        )


def _find_related_arguments(
    graph: GraphDB,
    statement: str,
    limit: int = 10,
) -> list[dict]:
    """Find arguments in the graph related to a statement.

    Uses keyword-based matching against argument text.
    For production, use Weaviate semantic search.
    """
    # Extract key words (longer than 3 chars, not common Hungarian stop words)
    stop_words = {
        "hogy", "egy", "van", "nem", "ezt", "azt", "ami", "aki",
        "mint", "már", "még", "csak", "kell", "volt", "lesz",
        "igen", "nem", "vagy", "és", "meg", "fel", "más",
    }
    words = [
        w for w in statement.lower().split()
        if len(w) > 3 and w not in stop_words
    ]

    if not words:
        return []

    # Search for arguments containing any of these keywords
    # (AGE doesn't have full-text search, so we do basic CONTAINS)
    results = []
    for word in words[:5]:  # Limit to 5 keywords
        try:
            found = graph.query(
                f"""
                MATCH (a:Argument)
                WHERE a.text CONTAINS '{word}'
                OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
                RETURN a.text, a.summary, p.shortname
                LIMIT 3
                """,
                columns=["text", "summary", "party"],
            )
            results.extend(found)
        except Exception:
            continue

    # Deduplicate by text
    seen = set()
    unique = []
    for r in results:
        text = r.get("text", "")
        if text not in seen:
            seen.add(text)
            unique.append(r)

    return unique[:limit]


def _find_rebuttals(
    graph: GraphDB,
    statement: str,
    limit: int = 5,
) -> list[dict]:
    """Find rebuttals to arguments related to the statement."""
    related = _find_related_arguments(graph, statement, limit=3)

    rebuttals = []
    for arg in related:
        text = arg.get("text", "").replace("'", "\\'")
        if not text:
            continue
        try:
            found = graph.query(
                f"""
                MATCH (r:Argument)-[:REBUTS]->(a:Argument {{text: '{text}'}})
                OPTIONAL MATCH (r)-[:MADE_BY]->(p:Party)
                RETURN r.text, r.summary, p.shortname
                """,
                columns=["text", "summary", "party"],
            )
            rebuttals.extend(found)
        except Exception:
            continue

    return rebuttals[:limit]
