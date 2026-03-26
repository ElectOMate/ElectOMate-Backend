"""Reusable Cypher query templates for the argument knowledge graph."""

from __future__ import annotations

# ============================================================================
# NODE CREATION
# ============================================================================

CREATE_ARGUMENT = """
MERGE (a:Argument {text: $text})
SET a.type = $type,
    a.summary = $summary,
    a.argument_type = $argument_type,
    a.confidence = $confidence,
    a.sentiment = $sentiment,
    a.strength = $strength,
    a.extraction_date = $extraction_date
RETURN a
"""

CREATE_POLITICIAN = """
MERGE (p:Politician {name: $name})
SET p.role = $role,
    p.active = $active
RETURN p
"""

CREATE_SOURCE = """
MERGE (s:Source {url: $url})
SET s.type = $source_type,
    s.title = $title,
    s.date = $date,
    s.modality = $modality
RETURN s
"""

CREATE_STATEMENT = """
CREATE (st:Statement {
    text: $text,
    context: $context,
    timestamp_in_source: $timestamp
})
RETURN st
"""

CREATE_POLIS_QUESTION = """
CREATE (pq:PolisQuestion {
    text: $text,
    question_type: $question_type
})
RETURN pq
"""

# ============================================================================
# RELATIONSHIPS
# ============================================================================

LINK_ARGUMENT_TO_TOPIC = """
MATCH (a:Argument {text: $arg_text})
MATCH (t:Topic {name: $topic_name})
MERGE (a)-[:ABOUT]->(t)
"""

LINK_ARGUMENT_TO_PARTY = """
MATCH (a:Argument {text: $arg_text})
MATCH (p:Party {shortname: $party_shortname})
MERGE (a)-[:MADE_BY]->(p)
"""

LINK_ARGUMENT_TO_POLITICIAN = """
MATCH (a:Argument {text: $arg_text})
MATCH (pol:Politician {name: $politician_name})
MERGE (a)-[:MADE_BY]->(pol)
"""

LINK_ARGUMENT_TO_SOURCE = """
MATCH (a:Argument {text: $arg_text})
MATCH (s:Source {url: $source_url})
MERGE (a)-[:SOURCED_FROM]->(s)
"""

LINK_ARGUMENT_SUPPORTS = """
MATCH (a1:Argument {text: $arg1_text})
MATCH (a2:Argument {text: $arg2_text})
MERGE (a1)-[:SUPPORTS]->(a2)
"""

LINK_ARGUMENT_REBUTS = """
MATCH (a1:Argument {text: $arg1_text})
MATCH (a2:Argument {text: $arg2_text})
MERGE (a1)-[:REBUTS]->(a2)
"""

LINK_ARGUMENT_CONTRADICTS = """
MATCH (a1:Argument {text: $arg1_text})
MATCH (a2:Argument {text: $arg2_text})
MERGE (a1)-[:CONTRADICTS]->(a2)
"""

LINK_POLITICIAN_TO_PARTY = """
MATCH (pol:Politician {name: $politician_name})
MATCH (p:Party {shortname: $party_shortname})
MERGE (pol)-[:MEMBER_OF]->(p)
"""

LINK_STATEMENT_TO_SPEAKER = """
MATCH (st:Statement {text: $statement_text})
MATCH (pol:Politician {name: $politician_name})
MERGE (st)-[:SPOKEN_BY]->(pol)
"""

LINK_POLIS_TO_ARGUMENT = """
MATCH (pq:PolisQuestion {text: $question_text})
MATCH (a:Argument {text: $arg_text})
MERGE (pq)-[:DERIVED_FROM]->(a)
"""

LINK_TOPIC_SUBTOPIC = """
MATCH (parent:Topic {name: $parent_name})
MATCH (child:Topic {name: $child_name})
MERGE (child)-[:SUBTOPIC_OF]->(parent)
"""

# ============================================================================
# QUERIES
# ============================================================================

GET_ARGUMENTS_BY_TOPIC = """
MATCH (a:Argument)-[:ABOUT]->(t:Topic {name: $topic_name})
OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
OPTIONAL MATCH (a)-[:MADE_BY]->(pol:Politician)
RETURN a, p, pol
"""

GET_ARGUMENTS_BY_PARTY = """
MATCH (a:Argument)-[:MADE_BY]->(p:Party {shortname: $party_shortname})
OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
RETURN a, t
"""

GET_ARGUMENTS_BY_TOPIC_AND_PARTY = """
MATCH (a:Argument)-[:ABOUT]->(t:Topic {name: $topic_name})
MATCH (a)-[:MADE_BY]->(p:Party {shortname: $party_shortname})
RETURN a
"""

GET_REBUTTALS = """
MATCH (a:Argument {text: $arg_text})<-[:REBUTS]-(r:Argument)
OPTIONAL MATCH (r)-[:MADE_BY]->(p:Party)
RETURN r, p
"""

GET_ARGUMENT_CHAIN = """
MATCH path = (a:Argument {text: $arg_text})-[:SUPPORTS|REBUTS|CONTRADICTS*1..3]-(related:Argument)
RETURN path
"""

COMPARE_PARTIES_ON_TOPIC = """
MATCH (a:Argument)-[:ABOUT]->(t:Topic {name: $topic_name})
MATCH (a)-[:MADE_BY]->(p:Party)
RETURN p.shortname as party, collect(a.summary) as arguments, count(a) as count
ORDER BY count DESC
"""

MOST_CONTESTED_TOPICS = """
MATCH (a1:Argument)-[:REBUTS]->(a2:Argument)
MATCH (a1)-[:ABOUT]->(t:Topic)
RETURN t.name as topic, count(*) as rebuttal_count
ORDER BY rebuttal_count DESC
LIMIT $limit
"""

POLITICIAN_ARGUMENT_HISTORY = """
MATCH (a:Argument)-[:MADE_BY]->(pol:Politician {name: $politician_name})
OPTIONAL MATCH (a)-[:SOURCED_FROM]->(s:Source)
OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
RETURN a, s, t
ORDER BY s.date DESC
"""

GET_ALL_TOPICS = """
MATCH (t:Topic)
OPTIONAL MATCH (a:Argument)-[:ABOUT]->(t)
RETURN t.name as name, t.name_en as name_en, t.category as category, count(a) as argument_count
ORDER BY argument_count DESC
"""

GET_ALL_PARTIES = """
MATCH (p:Party)
OPTIONAL MATCH (a:Argument)-[:MADE_BY]->(p)
RETURN p.shortname as shortname, p.name as name, p.ideology as ideology, count(a) as argument_count
ORDER BY argument_count DESC
"""
