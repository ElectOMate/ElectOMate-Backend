# Hungarian Political Knowledge Graph

A knowledge graph system for Hungarian political arguments built on Apache AGE (PostgreSQL graph extension) with pgvector semantic embeddings.

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

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Apache AGE (PostgreSQL) | `5433` (local) / `5432` (Docker internal) | Graph database with pgvector |
| Backend API | `8000` | FastAPI — graph endpoints at `/v2/graph/*` |
| Graph Explorer UI | `9001` | React + React Flow visualization |

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

## Quick Start

### 1. Start the AGE database

```bash
docker compose up age-postgres -d
```

This starts PostgreSQL 18 with Apache AGE + pgvector extensions on port **5433**.

### 2. Set environment variables

```bash
export AGE_POSTGRES_URL="host=localhost port=5433 dbname=age_graph user=postgres password=postgres"
export OPENAI_API_KEY="your-key-here"
```

### 3. Build the graph

```bash
python -m em_backend.graph.builder
```

### 4. Run the MCP server (for Claude Code)

Configured in `.mcp.json` at project root. Requires `AGE_POSTGRES_URL` and `OPENAI_API_KEY` in environment.

### 5. Start the Graph Explorer UI

```bash
cd graph-explorer
npm install
npm run dev   # http://localhost:9001
```

The UI proxies API calls to `http://localhost:9000` (backend).

## External Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| Browser Use API | `https://api.browser-use.com/api/v1` | Gov website scraping |
| Hungarian Parliament API | `https://www.parlament.hu/w-api-tajekoztato` | Register via `api-reg2@parlament.hu` |
| Google AI Studio (API keys) | `https://aistudio.google.com/apikey` | For Gemini/Google API keys |
