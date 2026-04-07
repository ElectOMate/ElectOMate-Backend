---
name: kg-graph-agent
description: Search, query, and extend the Hungarian Political Knowledge Graph
triggers:
  - "search the knowledge graph"
  - "find arguments about"
  - "add argument to graph"
  - "query political positions"
  - "knowledge graph"
  - "kg search"
  - "kg add"
  - "hungarian politics"
---

# Knowledge Graph Agent

Search, query, and extend the Hungarian Political Knowledge Graph.

## Prerequisites

- AGE PostgreSQL running on port 5433: `docker compose -f docker-compose.graph.yml up age-postgres -d`
- Working directory: `ElectOMate-Backend/`
- Use `.venv/bin/python` (not system python)

## Operations

### 1. Search by Text (Semantic Similarity)

Find arguments semantically close to a query:

```bash
AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres" \
.venv/bin/python scripts/kg_cli.py search "QUERY_TEXT"
```

### 2. Add New Argument (Dedup + Continuations)

Submit a new argument. Automatically checks for duplicates and generates 2-5 continuation arguments:

```bash
AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres" \
.venv/bin/python scripts/kg_cli.py add "ARGUMENT_TEXT" --party PARTY_SHORTNAME --topic TOPIC_NAME
```

Valid parties: FIDESZ, TISZA, DK, MI_HAZANK, MKKP, JOBBIK, MSZP
Valid topics: Gazdaság, EU-kapcsolatok, Migráció, Egészségügy, Oktatás, Honvédelem, Szociálpolitika, Sajtószabadság, Korrupció, Jogállamiság, Energia, Környezetvédelem, Ukrajna-háború, Lakhatás

### 3. Query by Topic/Party

```bash
AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres" \
.venv/bin/python scripts/kg_cli.py query --topic Egészségügy --party MSZP
```

### 4. Graph Stats

```bash
AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres" \
.venv/bin/python scripts/kg_cli.py stats
```

### 5. Full Rebuild

```bash
.venv/bin/python scripts/rebuild_hungarian_graph.py
```

## Architecture

- Graph DB: Apache AGE (PostgreSQL extension) on port 5433
- Embeddings: BGE-M3 (1024-dim) stored in pgvector
- LLM: GPT-4o for extraction, dedup judgment, continuation generation
- Graph name: `hungarian_politics`
