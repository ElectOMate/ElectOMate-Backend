"""MCP server exposing the Hungarian Political Knowledge Graph for Claude Code.

Run: python -m em_backend.graph.mcp_server
"""

from __future__ import annotations

import json
import os

import psycopg2
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("hungarian-politics-kg")

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
def search_arguments(query: str, limit: int = 20) -> str:
    """Semantic search over Hungarian political arguments using BGE-M3 embeddings.

    This uses hybrid retrieval: vector similarity + graph traversal + Reciprocal Rank Fusion.
    Much smarter than keyword search — finds paraphrases and related concepts.

    Args:
        query: Free-text search query in Hungarian or English.
        limit: Max results (default 20).

    Returns:
        JSON list of semantically similar arguments with similarity scores.
    """
    from em_backend.graph.hybrid_retrieval import hybrid_search
    results = hybrid_search(query, limit=limit)
    # Clean up for JSON serialization
    for r in results:
        r.pop("embedding", None)
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def query_arguments(
    topic: str | None = None,
    party: str | None = None,
    limit: int = 20,
) -> str:
    """Search Hungarian political arguments by topic and/or party (exact match).

    For semantic/fuzzy search, use search_arguments instead.

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

    Uses semantic similarity to find the closest argument in the graph,
    then traverses REBUTS and CONTRADICTS edges. Also returns semantically
    similar counter-arguments from opposing parties.

    Args:
        argument_text: The claim to find counter-arguments for.

    Returns:
        JSON list of rebutting/contradicting arguments with party attribution.
    """
    from em_backend.graph.embeddings import find_similar_to_text

    results = []

    # 1. Find semantically similar arguments
    similar = find_similar_to_text(argument_text, limit=5, min_similarity=0.5)

    # 2. For each similar argument, check for REBUTS/CONTRADICTS edges
    for s in similar:
        text = s["text"][:200].replace("'", "\\'")
        for rel in ["REBUTS", "CONTRADICTS"]:
            try:
                found = _cypher(
                    f"MATCH (a:Argument)-[:{rel}]->(b:Argument) "
                    f"WHERE b.text STARTS WITH '{text}' "
                    f"OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party) "
                    f"RETURN a.text, p.shortname, '{rel}' LIMIT 5",
                    columns=["text", "party", "relation"],
                )
                results.extend(found)
            except Exception:
                pass
            # Also reverse direction
            try:
                found = _cypher(
                    f"MATCH (b:Argument)-[:{rel}]->(a:Argument) "
                    f"WHERE b.text STARTS WITH '{text}' "
                    f"OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party) "
                    f"RETURN a.text, p.shortname, '{rel}' LIMIT 5",
                    columns=["text", "party", "relation"],
                )
                results.extend(found)
            except Exception:
                pass

    # 3. Deduplicate
    seen = set()
    unique = []
    for r in results:
        key = str(r.get("text", ""))[:80]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return json.dumps(unique, ensure_ascii=False, indent=2)


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
    from openai import OpenAI

    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if not oai_key:
        return json.dumps({"error": "OPENAI_API_KEY not set"})

    # Find related arguments in graph
    related = _cypher(
        f"MATCH (a:Argument) WHERE a.text CONTAINS '{statement[:50].replace(chr(39), '')}' "
        f"OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party) "
        f"RETURN a.text, p.shortname LIMIT 5",
        columns=["text", "party"],
    )
    # Also search by topic keywords
    keywords = [w for w in statement.lower().split() if len(w) > 4]
    for kw in keywords[:3]:
        try:
            found = _cypher(
                f"MATCH (a:Argument) WHERE a.text CONTAINS '{kw}' "
                f"OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party) "
                f"RETURN a.text, p.shortname LIMIT 3",
                columns=["text", "party"],
            )
            related.extend(found)
        except Exception:
            pass

    related_text = "\n".join(f"- [{r.get('party','?')}] {r.get('text','')}" for r in related[:8])
    vote_desc = {"agree": "AGREED with", "disagree": "DISAGREED with", "pass": "PASSED on"}.get(vote, "voted on")

    client = OpenAI(api_key=oai_key)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": (
            f'A user has {vote_desc}: "{statement}"\n\n'
            f"Related arguments from the knowledge graph:\n{related_text}\n\n"
            "Generate 5 follow-up Pol.is statements IN HUNGARIAN.\n"
            "Types: clarifying, probing, contrasting, deepening\n\n"
            'Return JSON: {"follow_ups": [{"text": "...", "question_type": "...", "rationale": "..."}]}'
        )}],
        response_format={"type": "json_object"},
        max_tokens=2000,
        temperature=0.7,
    )
    return resp.choices[0].message.content or "{}"


@mcp.tool()
def generate_polis_seeds(topic: str, count: int = 5) -> str:
    """Generate seed statements for a new Pol.is conversation on a topic.

    Args:
        topic: Topic name in Hungarian (e.g., "Gazdaság", "Jogállamiság").
        count: Number of statements to generate (1-10).

    Returns:
        JSON list of balanced, voteable statements with controversy scores.
    """
    from openai import OpenAI

    oai_key = os.environ.get("OPENAI_API_KEY", "")
    if not oai_key:
        return json.dumps({"error": "OPENAI_API_KEY not set"})

    t = topic.replace("'", "\\'")
    args_by_party = _cypher(
        f"MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}}) "
        f"MATCH (a)-[:MADE_BY]->(p:Party) "
        f"RETURN p.shortname, a.text LIMIT 20",
        columns=["party", "text"],
    )

    formatted = ""
    by_party: dict[str, list[str]] = {}
    for r in args_by_party:
        by_party.setdefault(str(r["party"]), []).append(str(r["text"]))
    for party, texts in by_party.items():
        formatted += f"\n[{party}]:\n"
        for t_text in texts[:3]:
            formatted += f"  - {t_text[:150]}\n"

    client = OpenAI(api_key=oai_key)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": (
            f'Generate {min(count, 10)} balanced Pol.is seed statements about "{topic}" in Hungarian politics.\n\n'
            f"Arguments from the knowledge graph:\n{formatted}\n\n"
            "Rules: Hungarian, max 140 chars, voteable, balanced, don't attribute.\n\n"
            '{"statements": [{"text": "...", "controversy_score": 0.0-1.0}]}'
        )}],
        response_format={"type": "json_object"},
        max_tokens=1500,
        temperature=0.8,
    )
    return resp.choices[0].message.content or "{}"


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
    escaped = node_name.replace("'", "\\'")
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    if node_type == "Topic":
        prop, root_id = "name", f"topic::{node_name}"
    elif node_type == "Party":
        prop, root_id = "shortname", f"party::{node_name}"
    else:
        prop, root_id = "text", f"arg::{node_name[:80]}"

    nodes[root_id] = {"id": root_id, "type": node_type, "label": node_name[:120], "properties": {}}

    if node_type == "Topic":
        results = _cypher(
            f"MATCH (a:Argument)-[:ABOUT]->(t:Topic {{{prop}: '{escaped}'}}) "
            f"OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party) "
            f"RETURN a.text, a.argument_type, a.sentiment, a.strength, p.shortname LIMIT 30",
            columns=["text", "arg_type", "sentiment", "strength", "party"],
        )
        for r in results:
            text = str(r.get("text", ""))
            aid = f"arg::{text[:80]}"
            nodes[aid] = {"id": aid, "type": "Argument", "label": text[:120], "properties": dict(r)}
            edges.append({"source": aid, "target": root_id, "type": "ABOUT"})
            party = r.get("party")
            if party:
                pid = f"party::{party}"
                if pid not in nodes:
                    nodes[pid] = {"id": pid, "type": "Party", "label": str(party), "properties": {}}
                edges.append({"source": aid, "target": pid, "type": "MADE_BY"})

    elif node_type == "Party":
        results = _cypher(
            f"MATCH (a:Argument)-[:MADE_BY]->(p:Party {{{prop}: '{escaped}'}}) "
            f"OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic) "
            f"RETURN a.text, a.argument_type, a.sentiment, t.name LIMIT 30",
            columns=["text", "arg_type", "sentiment", "topic"],
        )
        for r in results:
            text = str(r.get("text", ""))
            aid = f"arg::{text[:80]}"
            nodes[aid] = {"id": aid, "type": "Argument", "label": text[:120], "properties": dict(r)}
            edges.append({"source": aid, "target": root_id, "type": "MADE_BY"})
            topic = r.get("topic")
            if topic:
                tid = f"topic::{topic}"
                if tid not in nodes:
                    nodes[tid] = {"id": tid, "type": "Topic", "label": str(topic), "properties": {}}
                edges.append({"source": aid, "target": tid, "type": "ABOUT"})

    return json.dumps({"nodes": list(nodes.values()), "edges": edges}, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
