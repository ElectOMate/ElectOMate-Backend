"""Pol.is seed statement generator.

Generates initial Pol.is conversation statements from the argument
knowledge graph, balanced across parties and topics.
"""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from em_backend.core.config import settings
from em_backend.graph.db import GraphDB, get_graph_db

logger = structlog.get_logger(__name__)


class SeedStatement(BaseModel):
    """A seed statement for a new Pol.is conversation."""

    text: str = Field(description="The statement text (Hungarian)")
    topic: str = Field(description="Primary topic category")
    source_party: str | None = Field(
        default=None,
        description="Party whose argument inspired this statement",
    )
    controversy_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Expected controversy (0=consensus, 1=very divisive)",
    )


class SeedResult(BaseModel):
    """Result of seed statement generation."""

    topic: str
    statements: list[SeedStatement]


SEED_PROMPT = """Generate {count} balanced Pol.is seed statements about "{topic}" in Hungarian politics.

EXISTING ARGUMENTS FROM THE KNOWLEDGE GRAPH:
{arguments_by_party}

RULES:
1. Write in Hungarian (magyar nyelven)
2. Each statement must be concise (max 140 characters ideal)
3. Statements should be voteable (agree/disagree)
4. Balance across the political spectrum (government and opposition)
5. Include both broad policy positions and specific measures
6. Vary the controversy level (some consensus, some divisive)
7. Do NOT attribute statements to parties — make them neutral/general

Return JSON:
{{
  "statements": [
    {{
      "text": "Hungarian statement",
      "topic": "{topic}",
      "source_party": "PARTY_SHORT or null",
      "controversy_score": 0.0-1.0
    }}
  ]
}}"""


async def generate_seed_statements(
    topic: str,
    count: int = 10,
    graph: GraphDB | None = None,
) -> SeedResult:
    """Generate seed statements for a Pol.is conversation on a topic.

    Args:
        topic: Topic name (Hungarian) from the taxonomy.
        count: Number of statements to generate.
        graph: GraphDB instance.

    Returns:
        SeedResult with generated statements.
    """
    if graph is None:
        graph = get_graph_db()

    # Get existing arguments by party on this topic
    arguments_by_party = _get_arguments_by_party_for_topic(graph, topic)

    formatted_args = ""
    for party, args in arguments_by_party.items():
        formatted_args += f"\n[{party}]:\n"
        for arg in args[:5]:  # Max 5 per party
            formatted_args += f"  - {arg}\n"

    if not formatted_args.strip():
        formatted_args = "No arguments found in the graph for this topic."

    prompt = SEED_PROMPT.format(
        count=count,
        topic=topic,
        arguments_by_party=formatted_args,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.8,  # Higher creativity for diverse statements
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)

        statements = []
        for s_dict in parsed.get("statements", [])[:count]:
            try:
                statements.append(SeedStatement(**s_dict))
            except Exception as e:
                logger.warning("Failed to parse seed statement", error=str(e))

        return SeedResult(topic=topic, statements=statements)

    except Exception as e:
        logger.error("Seed statement generation failed", error=str(e))
        return SeedResult(topic=topic, statements=[])


async def generate_full_conversation_seeds(
    topics: list[str] | None = None,
    statements_per_topic: int = 5,
    graph: GraphDB | None = None,
) -> list[SeedResult]:
    """Generate seed statements for multiple topics.

    Args:
        topics: List of topic names. If None, uses all topics with arguments.
        statements_per_topic: Number of statements per topic.
        graph: GraphDB instance.

    Returns:
        List of SeedResults, one per topic.
    """
    if graph is None:
        graph = get_graph_db()

    if topics is None:
        # Get topics that have arguments
        from em_backend.graph.query_service import KnowledgeGraphService
        service = KnowledgeGraphService(graph)
        all_topics = service.get_all_topics()
        topics = [t.name for t in all_topics if t.argument_count > 0]

    results = []
    for topic in topics:
        logger.info("Generating seeds for topic", topic=topic)
        result = await generate_seed_statements(
            topic=topic,
            count=statements_per_topic,
            graph=graph,
        )
        results.append(result)

    total = sum(len(r.statements) for r in results)
    logger.info(
        "Full conversation seeds generated",
        topics=len(topics),
        total_statements=total,
    )
    return results


def _get_arguments_by_party_for_topic(
    graph: GraphDB,
    topic: str,
) -> dict[str, list[str]]:
    """Get argument summaries grouped by party for a topic."""
    try:
        escaped_topic = topic.replace("'", "\\'")
        results = graph.query(
            f"""
            MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{escaped_topic}'}})
            MATCH (a)-[:MADE_BY]->(p:Party)
            RETURN p.shortname, a.summary
            """,
            columns=["party", "summary"],
        )

        by_party: dict[str, list[str]] = {}
        for r in results:
            party = r.get("party", "Unknown")
            summary = r.get("summary", "")
            if summary:
                by_party.setdefault(party, []).append(summary)

        return by_party

    except Exception as e:
        logger.warning("Failed to get arguments by party", error=str(e))
        return {}
