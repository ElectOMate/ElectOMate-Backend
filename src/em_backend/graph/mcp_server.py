"""MCP server exposing the Hungarian Political Knowledge Graph for Claude Code.

Run: python -m em_backend.graph.mcp_server
"""

from __future__ import annotations

import json
import os

import psycopg2
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "hungarian-politics-kg",
    description="Hungarian Political Argument Knowledge Graph — query arguments, compare parties, find rebuttals, generate Pol.is questions",
)

# Connection config (override for local dev vs Docker)
AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)
GRAPH_NAME = "hungarian_politics"


def _get_conn():
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    return conn


def _cypher(cypher: str, columns: list[str] | None = None) -> list[dict]:
    """Execute a Cypher query and return results as dicts."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")

        col_defs = ", ".join(f"{c} agtype" for c in columns) if columns else "v agtype"
        sql = f"SELECT * FROM cypher('{GRAPH_NAME}', $$ {cypher} $$) as ({col_defs});"
        cur.execute(sql)
        rows = cur.fetchall()
        conn.commit()

        if columns:
            results = []
            for row in rows:
                d = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if isinstance(val, str):
                        val = val.strip('"')
                    d[col] = val
                results.append(d)
            return results
        return [{"v": str(row[0]).strip('"')} for row in rows]
    finally:
        conn.close()


# ============================================================================
# MCP Tools
# ============================================================================


@mcp.tool()
def query_arguments(
    topic: str | None = None,
    party: str | None = None,
    limit: int = 20,
) -> str:
    """Search Hungarian political arguments by topic and/or party.

    Args:
        topic: Topic name in Hungarian (e.g., "Gazdaság", "EU-kapcsolatok", "Korrupció")
        party: Party shortname (FIDESZ, TISZA, DK, MI_HAZANK, MKKP, JOBBIK, MSZP)
        limit: Max results (default 20)

    Returns:
        JSON list of arguments with claim text, type, sentiment, and strength.
    """
    if topic and party:
        t = topic.replace("'", "\\'")
        p = party.replace("'", "\\'")
        results = _cypher(
            f"""MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}})
            MATCH (a)-[:MADE_BY]->(p:Party {{shortname: '{p}'}})
            RETURN a.text, a.argument_type, a.sentiment, a.strength
            LIMIT {limit}""",
            columns=["text", "type", "sentiment", "strength"],
        )
    elif topic:
        t = topic.replace("'", "\\'")
        results = _cypher(
            f"""MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}})
            OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
            RETURN a.text, a.argument_type, a.sentiment, p.shortname
            LIMIT {limit}""",
            columns=["text", "type", "sentiment", "party"],
        )
    elif party:
        p = party.replace("'", "\\'")
        results = _cypher(
            f"""MATCH (a:Argument)-[:MADE_BY]->(p:Party {{shortname: '{p}'}})
            OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
            RETURN a.text, a.argument_type, a.sentiment, t.name
            LIMIT {limit}""",
            columns=["text", "type", "sentiment", "topic"],
        )
    else:
        results = _cypher(
            f"""MATCH (a:Argument)
            OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
            RETURN a.text, a.argument_type, p.shortname
            LIMIT {limit}""",
            columns=["text", "type", "party"],
        )

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_argument_chain(argument_text: str) -> str:
    """Get the full chain of supports/rebuts/contradicts around an argument.

    Args:
        argument_text: The claim text of the argument to explore.

    Returns:
        JSON with the argument and all related arguments (supports, rebuttals, contradictions).
    """
    escaped = argument_text.replace("'", "\\'")[:500]
    chain = {"root": argument_text, "supports": [], "rebuts": [], "contradicts": []}

    for rel, key in [("SUPPORTS", "supports"), ("REBUTS", "rebuts"), ("CONTRADICTS", "contradicts")]:
        try:
            results = _cypher(
                f"""MATCH (a:Argument {{text: '{escaped}'}})-[:{rel}]->(b:Argument)
                OPTIONAL MATCH (b)-[:MADE_BY]->(p:Party)
                RETURN b.text, p.shortname LIMIT 10""",
                columns=["text", "party"],
            )
            chain[key] = results
        except Exception:
            pass

        # Also check reverse direction
        try:
            results = _cypher(
                f"""MATCH (b:Argument)-[:{rel}]->(a:Argument {{text: '{escaped}'}})
                OPTIONAL MATCH (b)-[:MADE_BY]->(p:Party)
                RETURN b.text, p.shortname LIMIT 10""",
                columns=["text", "party"],
            )
            chain[f"{key}_by"] = results
        except Exception:
            pass

    return json.dumps(chain, ensure_ascii=False, indent=2)


@mcp.tool()
def find_rebuttals(argument_text: str) -> str:
    """Find arguments that rebut or contradict a given claim.

    Args:
        argument_text: The claim to find counter-arguments for.

    Returns:
        JSON list of rebutting arguments with party attribution.
    """
    escaped = argument_text.replace("'", "\\'")[:500]
    results = []

    for rel in ["REBUTS", "CONTRADICTS"]:
        try:
            found = _cypher(
                f"""MATCH (r:Argument)-[:{rel}]->(a:Argument {{text: '{escaped}'}})
                OPTIONAL MATCH (r)-[:MADE_BY]->(p:Party)
                RETURN r.text, p.shortname, '{rel}' LIMIT 10""",
                columns=["text", "party", "relation"],
            )
            results.extend(found)
        except Exception:
            pass

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def compare_parties(topic: str) -> str:
    """Compare all parties' positions on a political topic.

    Args:
        topic: Topic name in Hungarian (e.g., "Gazdaság", "EU-kapcsolatok")

    Returns:
        JSON mapping party shortname → list of argument summaries.
    """
    t = topic.replace("'", "\\'")
    results = _cypher(
        f"""MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}})
        MATCH (a)-[:MADE_BY]->(p:Party)
        RETURN p.shortname, a.text""",
        columns=["party", "text"],
    )

    by_party: dict[str, list[str]] = {}
    for r in results:
        party = str(r.get("party", "Unknown"))
        text = str(r.get("text", ""))
        by_party.setdefault(party, []).append(text)

    return json.dumps(by_party, ensure_ascii=False, indent=2)


@mcp.tool()
def get_topics() -> str:
    """List all political topics in the knowledge graph with argument counts.

    Returns:
        JSON list of topics with name (Hungarian), English name, category, and argument count.
    """
    results = _cypher(
        """MATCH (t:Topic)
        OPTIONAL MATCH (a:Argument)-[:ABOUT]->(t)
        RETURN t.name, t.name_en, t.category, count(a)
        ORDER BY count(a) DESC""",
        columns=["name", "name_en", "category", "argument_count"],
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_parties() -> str:
    """List all Hungarian political parties with argument counts.

    Returns:
        JSON list of parties with shortname, full name, ideology, and argument count.
    """
    results = _cypher(
        """MATCH (p:Party)
        OPTIONAL MATCH (a:Argument)-[:MADE_BY]->(p)
        RETURN p.shortname, p.name, p.ideology, count(a)
        ORDER BY count(a) DESC""",
        columns=["shortname", "name", "ideology", "argument_count"],
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_graph_stats() -> str:
    """Get knowledge graph statistics: total nodes, edges, and source breakdown.

    Returns:
        JSON with counts for each node type and edge type.
    """
    stats = {}
    for label in ["Argument", "Topic", "Party", "Politician", "Source"]:
        try:
            r = _cypher(f"MATCH (n:{label}) RETURN count(n)", columns=["cnt"])
            stats[label] = r[0]["cnt"] if r else 0
        except Exception:
            stats[label] = 0

    for rel in ["MADE_BY", "SOURCED_FROM", "ABOUT", "SUPPORTS", "REBUTS", "CONTRADICTS"]:
        try:
            r = _cypher(f"MATCH ()-[r:{rel}]->() RETURN count(r)", columns=["cnt"])
            stats[f"edge_{rel}"] = r[0]["cnt"] if r else 0
        except Exception:
            stats[f"edge_{rel}"] = 0

    return json.dumps(stats, ensure_ascii=False, indent=2)


@mcp.tool()
def generate_polis_followup(statement: str, vote: str) -> str:
    """Generate Pol.is follow-up questions based on a user's vote on a statement.

    This queries the knowledge graph for related arguments and uses GPT-4o
    to generate targeted follow-up questions in Hungarian.

    Args:
        statement: The Pol.is statement the user voted on (in Hungarian).
        vote: "agree", "disagree", or "pass".

    Returns:
        JSON with follow-up questions of types: clarifying, probing, contrasting, deepening.
    """
    import asyncio
    from em_backend.graph.polis.question_generator import generate_followups

    result = asyncio.run(generate_followups(statement=statement, user_vote=vote))
    return json.dumps(
        {
            "original": result.original_statement,
            "vote": result.user_vote,
            "follow_ups": [fu.model_dump() for fu in result.follow_ups],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def generate_polis_seeds(topic: str, count: int = 5) -> str:
    """Generate seed statements for a new Pol.is conversation on a topic.

    Args:
        topic: Topic name in Hungarian (e.g., "Gazdaság", "Jogállamiság").
        count: Number of statements to generate (1-10).

    Returns:
        JSON list of balanced, voteable statements with controversy scores.
    """
    import asyncio
    from em_backend.graph.polis.seed_generator import generate_seed_statements

    result = asyncio.run(generate_seed_statements(topic=topic, count=min(count, 10)))
    return json.dumps(
        {
            "topic": result.topic,
            "statements": [s.model_dump() for s in result.statements],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def get_neighborhood(node_type: str, node_name: str, depth: int = 1) -> str:
    """Get the graph neighborhood around a node for exploration.

    Args:
        node_type: "Topic", "Party", or "Argument"
        node_name: The node identifier (topic name, party shortname, or argument text)
        depth: 1 = direct neighbors, 2 = 2nd degree neighbors

    Returns:
        JSON with {nodes: [...], edges: [...]} for graph visualization.
    """
    from em_backend.graph.db import get_graph_db
    from em_backend.graph.query_service import KnowledgeGraphService

    graph = get_graph_db()
    service = KnowledgeGraphService(graph)
    result = service.get_neighborhood(node_type, node_name, depth)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
