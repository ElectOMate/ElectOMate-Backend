"""Knowledge graph schema creation and management.

Defines the argument ontology based on Walton's argumentation schemes
and the Argument Interchange Format (AIF).
"""

from __future__ import annotations

import structlog

from em_backend.graph.db import GraphDB, get_graph_db

logger = structlog.get_logger(__name__)

# Vertex label creation queries
VERTEX_LABELS = [
    "Argument",
    "Topic",
    "Party",
    "Politician",
    "Source",
    "Statement",
    "PolisQuestion",
]

# Sample seed data for Hungarian political topics
SEED_TOPICS = [
    {"name": "Gazdaság", "name_en": "Economy", "category": "economic",
     "keywords": ["adó", "gazdaság", "infláció", "GDP", "munkanélküliség", "bérek"]},
    {"name": "EU-kapcsolatok", "name_en": "EU Relations", "category": "foreign_policy",
     "keywords": ["EU-tagság", "szuverenitás", "Brüsszel", "európai"]},
    {"name": "Migráció", "name_en": "Migration", "category": "social",
     "keywords": ["migráció", "bevándorlás", "menekült", "határvédelem"]},
    {"name": "Egészségügy", "name_en": "Healthcare", "category": "social",
     "keywords": ["egészségügy", "kórház", "orvos", "beteg", "gyógyszer"]},
    {"name": "Oktatás", "name_en": "Education", "category": "social",
     "keywords": ["oktatás", "iskola", "tanár", "egyetem", "diák"]},
    {"name": "Honvédelem", "name_en": "Defense", "category": "foreign_policy",
     "keywords": ["honvédelem", "NATO", "hadsereg", "biztonság"]},
    {"name": "Szociálpolitika", "name_en": "Social Policy", "category": "social",
     "keywords": ["szociálpolitika", "nyugdíj", "segély", "szegénység", "család"]},
    {"name": "Sajtószabadság", "name_en": "Press Freedom", "category": "governance",
     "keywords": ["sajtószabadság", "média", "cenzúra", "újságíró"]},
    {"name": "Korrupció", "name_en": "Corruption", "category": "governance",
     "keywords": ["korrupció", "átláthatóság", "közbeszerzés", "oligarcha"]},
    {"name": "Jogállamiság", "name_en": "Rule of Law", "category": "governance",
     "keywords": ["jogállamiság", "bíróság", "alkotmány", "törvény", "igazságszolgáltatás"]},
    {"name": "Energia", "name_en": "Energy", "category": "economic",
     "keywords": ["energia", "rezsicsökkentés", "atomerőmű", "megújuló", "Paks"]},
    {"name": "Környezetvédelem", "name_en": "Environment", "category": "environment",
     "keywords": ["környezetvédelem", "klíma", "zöld", "szennyezés"]},
    {"name": "Ukrajna-háború", "name_en": "Ukraine War", "category": "foreign_policy",
     "keywords": ["Ukrajna", "háború", "béke", "szankció", "Oroszország"]},
    {"name": "Lakhatás", "name_en": "Housing", "category": "economic",
     "keywords": ["lakás", "lakhatás", "ingatlan", "albérlet", "hitel"]},
]

# Hungarian political parties (synced with ElectOMate data)
SEED_PARTIES = [
    {"shortname": "FIDESZ", "name": "Fidesz – Magyar Polgári Szövetség",
     "ideology": "national-conservative"},
    {"shortname": "TISZA", "name": "Tisza Párt",
     "ideology": "centre-right"},
    {"shortname": "DK", "name": "Demokratikus Koalíció",
     "ideology": "centre-left"},
    {"shortname": "MI_HAZANK", "name": "Mi Hazánk Mozgalom",
     "ideology": "far-right"},
    {"shortname": "MKKP", "name": "Magyar Kétfarkú Kutya Párt",
     "ideology": "satirical"},
    {"shortname": "JOBBIK", "name": "Jobbik Magyarországért Mozgalom",
     "ideology": "centre-right"},
    {"shortname": "MSZP", "name": "Magyar Szocialista Párt",
     "ideology": "social-democratic"},
]


def initialize_schema(graph: GraphDB | None = None) -> None:
    """Create all vertex labels and seed initial data.

    Apache AGE creates labels implicitly on first use with CREATE,
    but we explicitly create them for clarity and to enable indexing.
    """
    if graph is None:
        graph = get_graph_db()

    logger.info("Initializing knowledge graph schema...")

    # Create vertex labels by creating and deleting a dummy node
    # (AGE creates labels implicitly)
    for label in VERTEX_LABELS:
        try:
            graph.write(
                f"CREATE (n:{label} {{_init: true}}) RETURN n"
            )
            graph.write(
                f"MATCH (n:{label} {{_init: true}}) DELETE n"
            )
            logger.info("Created vertex label", label=label)
        except Exception:
            logger.debug("Label may already exist", label=label)

    # Seed topics
    for topic in SEED_TOPICS:
        graph.write(
            f"""MERGE (t:Topic {{name: '{topic["name"]}'}})
            SET t.name_en = '{topic["name_en"]}',
                t.category = '{topic["category"]}'
            RETURN t"""
        )
    logger.info("Seeded topics", count=len(SEED_TOPICS))

    # Seed parties
    for party in SEED_PARTIES:
        escaped_name = party["name"].replace("'", "\\'")
        graph.write(
            f"""MERGE (p:Party {{shortname: '{party["shortname"]}'}})
            SET p.name = '{escaped_name}',
                p.ideology = '{party["ideology"]}'
            RETURN p"""
        )
    logger.info("Seeded parties", count=len(SEED_PARTIES))

    logger.info("Knowledge graph schema initialized successfully")


def get_graph_stats(graph: GraphDB | None = None) -> dict[str, int]:
    """Get node and edge counts for each label/type."""
    if graph is None:
        graph = get_graph_db()

    stats = {}
    for label in VERTEX_LABELS:
        try:
            result = graph.query(
                f"MATCH (n:{label}) RETURN count(n)",
                columns=["cnt"],
            )
            stats[label] = result[0]["cnt"] if result else 0
        except Exception:
            stats[label] = 0

    return stats
