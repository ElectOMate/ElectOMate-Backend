# Hungarian Political Knowledge Graph

A knowledge graph system for Hungarian political arguments built on Apache AGE (PostgreSQL graph extension) with pgvector semantic embeddings.

## Quick Start

### Option A: Full stack via Docker (recommended)

```bash
cd ElectOMate-Backend

# 1. Copy and fill in env vars
cp .env.graph.example .env.graph
# Edit .env.graph — at minimum set OPENAI_API_KEY

# 2. Start everything (AGE DB + Backend API + React Explorer UI)
docker compose -f docker-compose.graph.yml up -d

# 3. On first run (or after DB wipe), rebuild the graph
docker compose -f docker-compose.graph.yml exec app python scripts/rebuild_hungarian_graph.py
```

After startup:

| Service | URL |
|---------|-----|
| **Graph Explorer UI** | http://localhost:9001 |
| **Backend API** | http://localhost:9000 |
| **AGE PostgreSQL** | `localhost:5433` |

### Option B: Local dev (piece by piece)

```bash
cd ElectOMate-Backend

# 1. Start just the AGE database
docker compose -f docker-compose.graph.yml up age-postgres -d

# 2. Set env vars (or use .env file)
export AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres"
export OPENAI_API_KEY="your-key-here"

# 3. Rebuild the graph from manifesto PDFs
.venv/bin/python scripts/rebuild_hungarian_graph.py

# 4. Start the backend API
.venv/bin/python -m uvicorn em_backend.main:app --port 9000

# 5. Start the Graph Explorer UI
cd graph-explorer && npm install && npm run dev   # http://localhost:9001
```

The UI proxies API calls to `http://localhost:9000` (backend).

## Rebuilding the Graph

If the database gets wiped or you need a fresh start:

```bash
# Full rebuild (schema + manifesto ingestion + enrichment + embeddings + relationships)
.venv/bin/python scripts/rebuild_hungarian_graph.py

# Skip expensive GPT-4o relationship detection
.venv/bin/python scripts/rebuild_hungarian_graph.py --skip-relationships

# Skip BGE-M3 embedding computation
.venv/bin/python scripts/rebuild_hungarian_graph.py --skip-embeddings

# Only create schema and seed data (topics + parties, no ingestion)
.venv/bin/python scripts/rebuild_hungarian_graph.py --schema-only
```

The rebuild script:
1. Creates the AGE graph and pgvector table
2. Seeds 14 Hungarian political topics and 7 parties
3. Extracts arguments from all 7 party manifesto PDFs (via GPT-4o)
4. Enriches with politicians, platforms, locations, organizations
5. Computes BGE-M3 embeddings and stores in pgvector
6. Detects SUPPORTS/REBUTS/CONTRADICTS relationships between arguments

**Requires:** `OPENAI_API_KEY` (for argument extraction) and AGE PostgreSQL running.

## Architecture

```
graph/
├── builder.py              # Graph ingestion pipeline orchestrator
├── db.py                   # Apache AGE database connection manager
├── embeddings.py           # BGE-M3 embedding service with pgvector
├── enrichment.py           # Argument enrichment pipeline
├── hybrid_retrieval.py     # Vector + graph traversal hybrid search (RRF fusion)
├── mcp_server.py           # MCP server for Claude Code integration
├── queries.py              # Low-level Cypher queries
├── query_service.py        # High-level graph query service
├── schema.py               # Graph schema + seed data (topics, parties)
├── connectors/
│   ├── base.py             # Base connector interface
│   ├── gov_scraper.py      # Government website scraper (Browser Use API)
│   ├── manifesto.py        # Manifesto Project connector
│   ├── parlamint.py        # ParlaMint parliamentary data connector
│   └── youtube.py          # YouTube video transcript extraction
├── extraction/
│   ├── argument_miner.py   # LLM-based argument extraction
│   ├── entity_resolver.py  # Party/politician entity resolution
│   ├── relationship_detector.py  # SUPPORTS/REBUTS/CONTRADICTS detection
│   └── topic_builder.py    # Topic classification for arguments
└── polis/
    ├── question_generator.py  # Generate follow-up questions
    └── seed_generator.py      # Generate seed statements for Pol.is
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v2/graph/topics` | List all topics |
| `GET /v2/graph/parties` | List all parties |
| `GET /v2/graph/stats` | Graph statistics |
| `GET /v2/graph/arguments` | Query arguments (topic/party filters) |
| `GET /v2/graph/compare/:topic` | Compare party positions on a topic |
| `GET /v2/graph/overview` | Full graph overview |
| `GET /v2/graph/neighborhood` | Node neighborhood for visualization |

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `AGE_POSTGRES_URL` | Apache AGE connection string | `host=localhost port=5433 dbname=age_graph user=postgres password=postgres` |
| `OPENAI_API_KEY` | GPT-4o for argument extraction, Pol.is generation, relationship detection | *(secret)* |

### Optional (per connector)

| Variable | Description | Used By |
|----------|-------------|---------|
| `BROWSERUSE_API_KEY` | Browser Use API for gov website scraping | `connectors/gov_scraper.py` |
| `GOOGLE_API_KEY` | Google API for YouTube transcription | `connectors/youtube.py` |
| `GEMINI_API_KEY` | Gemini API for video analysis | `connectors/youtube.py` |
| `PARLIAMENT_HU_API_TOKEN` | Hungarian Parliament API access | `connectors/parlamint.py` |
| `PERPLEXITY_API_KEY` | Perplexity AI for web research | MCP server |
| `PERPLEXITY_MODEL` | Perplexity model name (default: `sonar`) | MCP server |

### Non-secret configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ENV` | Environment (`dev` / `prod`) | `dev` |
| `VISION_ENABLED` | Enable vision capabilities | `true` |
| `VISION_MODEL` | Vision model name | `gpt-4o` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG` |

## MCP Server (Claude Code integration)

Configured in `.mcp.json` at project root. Requires `AGE_POSTGRES_URL` and `OPENAI_API_KEY` in environment.

## Troubleshooting

### DB was wiped / graph is empty
Run the rebuild script: `.venv/bin/python scripts/rebuild_hungarian_graph.py`

### `kg-frontend` stuck in restart loop
The frontend container depends on the backend (`app` service). Start the full stack:
`docker compose -f docker-compose.graph.yml up -d`

### Pydantic type errors on Python 3.13
Known issue with Pydantic 2.11 + Python 3.13. The `base.py` connector uses `Optional[X]` instead of `X | None` as a workaround.

### `argument_embeddings` table missing
The rebuild script creates it automatically. Or manually:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE argument_embeddings (
    id SERIAL PRIMARY KEY,
    argument_id TEXT UNIQUE NOT NULL,
    argument_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    party TEXT, topics TEXT[], speaker TEXT,
    arg_type TEXT, sentiment TEXT, source_date TEXT, platform TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_argument_embeddings_hnsw ON argument_embeddings USING hnsw (embedding vector_cosine_ops);
```

## External Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| Browser Use API | `https://api.browser-use.com/api/v1` | Gov website scraping |
| Hungarian Parliament API | `https://www.parlament.hu/w-api-tajekoztato` | Register via `api-reg2@parlament.hu` |
| Google AI Studio (API keys) | `https://aistudio.google.com/apikey` | For Gemini/Google API keys |
