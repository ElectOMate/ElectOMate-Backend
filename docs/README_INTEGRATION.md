# ElectOMate Backend Integration Guide

This document summarises the FastAPI surface exposed by `ElectOMate-Backend` and how the payloads map to the domain models. It is written for frontend developers who integrate the chat UI and the new-country workflow hosted in the separate project.

## Base Configuration

- **Base URL:** `http://localhost:8000`
- **API prefix:** All functional endpoints live under `/v2`.
- **Authentication:** None (development); add a reverse proxy or auth layer beforehand for production.
- **Content types:** JSON for CRUD endpoints, `multipart/form-data` for document uploads, Server Sent Events (SSE) for chat streaming.

During application startup (`v2.lifespan`) the backend creates singletons for:

1. `VectorDatabase` (Weaviate client) configured via environment (`WV_URL`, `WV_API_KEY`, `OPENAI_API_KEY`).
2. Database session factory created against `settings.postgres_url`.
3. `Agent` orchestrator for chat responses.
4. `DocumentParser` (Docling + OpenAI tokenizer) used during ingestion.

Keep the `.env` in sync with the frontend deployment – missing keys will break the `/v2/documents/` ingestion pipeline and the chat agent.

## Domain CRUD Endpoints

Every CRUD route follows the same `skip` + `limit` pagination scheme and returns Pydantic models declared in `src/em_backend/models/crud.py`.

### Countries (`/v2/countries/`)

- `POST /v2/countries/` – create a country. Body: `{ "name": str, "code": str(2) }`.
- `GET /v2/countries/?skip=0&limit=100` – list countries.
- `GET /v2/countries/{country_id}` – fetch a single country by UUID.
- `PUT /v2/countries/{country_id}` – update selected fields.
- `DELETE /v2/countries/{country_id}` – delete cascade (SQLAlchemy relationships remove elections/parties/documents automatically via FK constraints).

`code` is unique and stored uppercase in PostgreSQL (`CHAR(2)`).

### Elections (`/v2/elections/`)

- `POST /v2/elections/` body matches `ElectionCreate`:
  ```json
  {
    "name": "Chilean general election",
    "year": 2025,
    "date": "2025-11-16T00:00:00",
    "url": "https://…",
    "wv_collection": "D2025chileangeneralelection",
    "country_id": "<uuid>"
  }
  ```
  The backend checks the referenced country and lazily creates a Weaviate collection when missing.
- `GET /v2/elections/` with pagination.
- `GET /v2/elections/{election_id}`.
- `PUT /v2/elections/{election_id}` to update metadata (including `wv_collection`).
- `DELETE /v2/elections/{election_id}` also removes the associated Weaviate collection if it exists.

### Parties (`/v2/parties/`)

- `POST /v2/parties/` body (`PartyCreate`):
  ```json
  {
    "shortname": "FUT",
    "fullname": "Future Party",
    "description": "Optional",
    "url": "https://…",
    "election_id": "<uuid>"
  }
  ```
  Requires the election to exist. `shortname` is used in chat requests and new-country flows.
- Full CRUD semantics available with identical patterns as other resources.

### Candidates (`/v2/candidates/`)

- `POST /v2/candidates/` body (`CandidateCreate`):
  ```json
  {
    "given_name": "Maria",
    "family_name": "Rojas",
    "description": "Optional",
    "url": "https://…",
    "party_id": "<uuid>"
  }
  ```
- `GET /v2/candidates/` (paginated), `GET /{candidate_id}`, `PUT`, `DELETE` behave as expected.

### Documents (`/v2/documents/`)

Used to ingest manifestos or other party material. The upload triggers parsing and Weaviate indexing in the background.

- `POST /v2/documents/` (`multipart/form-data`):
  - `file`: manifesto binary.
  - `party_id`: UUID referencing `Party`.
  - `is_document_already_parsed`: optional flag. When `false` (default) the backend parses and indexes the document asynchronously.

  Example `curl`:
  ```bash
  curl -X POST "http://localhost:8000/v2/documents/" \
       -F "file=@/path/to/manifesto.pdf" \
       -F "party_id=6c7d…" \
       -F "is_document_already_parsed=false"
  ```

- `GET /v2/documents/` returns metadata only.
- `GET /v2/documents/{document_id}` includes the parsed markdown content.
- `PUT /v2/documents/{document_id}` allows updating metadata or content manually.
- `DELETE /v2/documents/{document_id}` removes the DB row and calls `VectorDatabase.delete_chunks` to purge vectors for the associated document.

Supported formats match the `SupportedDocumentFormats` enum (`pdf`, `docx`, `xlsx`, `pptx`, `markdown`, `ascii`, `html`, `xhtml`, `csv`).

### Proposed Questions (`/v2/proposed-questions/`)

Stores curated follow-up questions per party.

- `POST /v2/proposed-questions/` body (`ProposedQuestionCreate`):
  ```json
  {
    "question": "How will …",
    "cached_answer": null,
    "party_id": "<uuid>"
  }
  ```
- Standard GET/PUT/DELETE endpoints mirror other resources.

## Agent Chat (`/v2/agent/chat`)

The chat endpoint streams Server Sent Events to power the multi-party conversation UI.

### Request Schema

- Method: `POST`
- Path: `/v2/agent/chat`
- Body (`application/json`):
  ```json
  {
    "messages": [
      { "type": "assistant", "content": "Prior system output" },
      { "type": "user", "content": "What are the top priorities?" }
    ],
    "election_id": "<uuid>",
    "selected_parties": ["FUT", "LIB", "LAB"],
    "use_vector_database": true,
    "use_web_search": false
  }
  ```

Constraints and behaviour:

- `messages` is a discriminated union (`type` = `user` | `assistant`). The final entry **must** be a `user` message (`AfterValidator` enforces this).
- `selected_parties` must contain party `shortname` values that exist for the supplied election; missing names produce a 404 response.
- `election_id` must reference an existing election. The backend reopens a fresh DB session per streamed response to avoid early session closure.

### Response Stream

The endpoint returns `text/event-stream`. Each chunk conforms to `AnyChunk` from `src/em_backend/models/chunks.py`, with the `event` field set to the chunk `type`. Key chunk types:

- `party_response` – tokenised answer for a single party (`content` string + `party`).
- `party_response_sources` – array of Weaviate `DocumentChunk` records backing the answer.
- `party_message_chunk` – intermediate chat message associated with a party.
- `comparison_response` / `comparison_response_sources` – comparative narrative and supporting citations across parties.
- `message` – generic assistant/user messages.
- `title` – conversation title suggestion.
- `follow_up` – list of follow-up questions.

The frontend should parse SSE events, decode each JSON payload, and update party-specific streams accordingly.

## Data Relationships

Entity graph (see `database/models.py`):

- `Country` ↔ `Election` (1:N)
- `Election` ↔ `Party` (1:N)
- `Party` ↔ `Candidate` (1:1)
- `Party` ↔ `Document` (1:N)
- `Party` ↔ `ProposedQuestion` (1:N)

This hierarchy mirrors the new-country workflow: create a country, then an election, add parties, attach candidate details, upload manifestos/documents, and finally push proposed questions.

## Suggested Frontend Workflow

1. **Country setup**
   - Check or create the country via `POST /v2/countries/`.
2. **Election creation**
   - Create the election and retain the returned `id` and `wv_collection`. The frontend should pass the election `id` into chat requests.
3. **Parties**
   - For each discovered party, call `POST /v2/parties/`.
   - Store the `shortname` for later use in `selected_parties`.
4. **Candidates (optional)**
   - Populate candidate info for each party with `POST /v2/candidates/`.
5. **Manifesto ingestion**
   - Upload PDFs using `POST /v2/documents/` (multipart) per party.
   - Monitor backend logs for parsing/indexing success (fields transition from `no_parsing` / `no_indexing` to final values).
6. **Curated content**
   - Store additional prompts/questions with `POST /v2/proposed-questions/`.
7. **Chat usage**
   - Invoke `/v2/agent/chat` with the election id and the party shortnames relevant to the UX.

## Notes for Frontend Refactors

- Update `API.tsx` and `API2.tsx` to serialise `messages` as described above, include `election_id`, and map front-end party identifiers to backend `shortname`s.
- Ensure the frontend respects SSE semantics: reconnect on network failure, buffer partial JSON lines if necessary, and handle the terminal `DONE` event.
- When integrating the `new_country_routes.py` workflow, use the CRUD endpoints to persist final selections into the backend (countries/elections/parties/candidates) before triggering document uploads so the chat agent can resolve them.

## Troubleshooting

- 404 errors for chat normally indicate unresolved parties – confirm that `selected_parties` match `Party.shortname` exactly (case-sensitive).
- Document uploads that fail leave `parsing_quality = "failed"` or `indexing_success = "failed"`. Check the backend logs for docling errors, or set `is_document_already_parsed=true` to skip parsing if you provide pre-processed content.
- `VectorDatabase` connectivity requires valid Weaviate and OpenAI keys. Missing headers throw runtime errors during startup.

## Frontend Clients (`API.tsx`, `API2.tsx`)

`ElectOMate-Frontend/src/components/API.tsx` contains the legacy REST helpers used in the classic chat UI. The important functions are:

- `sendMessageToBackend_Stream(text, setter, setIsSending, languageCode)` — opens an `EventSource` to `/v1/chat/stream` (legacy path) and emits chunks to `setter`. This will be retired once the UI migrates to `/v2/agent/chat`.
- `sendMessageToBackend_multi(request, setMessages, setIsSending)` — POSTs JSON without SSE support; used by the multi-party view pre-refresh.

`API2.tsx` is the refreshed client that already streams from the `/v2` router:

```ts
sendToUnifiedAPI(
  {
    question: userMessageText,
    use_web_search: chatMode === "search",
    use_database_search: chatMode !== "search",
    selectedParties: [...],          // enum values mapping to backend shortnames
    countryCode: SupportedLanguages,
  },
  handleChunk,
  onError,
)
```

- The function resolves `SupportedParties` enums to `shortname` strings and sends a POST to `http://localhost:8000/v2/agent/chat`.
- It keeps the network connection open, reading `event/data` pairs from the SSE stream and dispatching them into `handleChunk`. The chunk types mirror `AnyChunk` defined on the backend.
- `use_database_search` toggles Weaviate usage; `use_web_search` is reserved for future connectors and currently proxies the boolean through to the backend request body.
- Errors invoke `onError`, allowing the UI to replace the pending bot message with a fallback error string.

To follow the new contract, the frontend must ensure:

1. `selectedParties` resolves to backend `Party.shortname` values.
2. `countryCode` is purely UI metadata (e.g., locale). The backend requires `election_id` inside the SSE payload; add that when mapping UI state to the request body.
3. `handleChunk` converts stream chunks into `ChatMessage` entries. Any new chunk types added server-side should be handled here to avoid dropping structured answers.

## New-Country Workflow (Frontend Modules)

`ElectOMate-Frontend/src/pages/NewCountryPage/` orchestrates the country set-up wizard. The main component (`NewCountryPage.tsx`) owns the step progression and delegates to sub-components located under `components/`. Key responsibilities per module:

- `PartySelect.tsx` — displays discovered parties, enables rename/delete, lets users upload logos via the AutoCreate backend (`/new-country/drafts/{code}/upload-logo`).
- `ManifestoStep.tsx` & `ManifestoUpload.tsx` — wraps the manifesto uploader. Uploads send `multipart/form-data` to AutoCreate (`/new-country/drafts/{code}/upload-manifesto`). Files are stored on disk and referenced in `PartiesJson.json`.
- `QuestionGenerationStep.tsx` — drives the multi-stage “QGen” job tree (`/qgen/*` endpoints). Each button call hits AutoCreate which orchestrates LLM prompts and writes intermediate JSON artifacts.
- `QuestionnaireStep.tsx` — kicks off the indexing/evaluation pipeline (`/indexing/*`). When results arrive, it renders `EvaluationResults.tsx` for manual review.
- `EvaluationResults.tsx` — fetches evaluation JSON, allows approving party answers, and persists edits back via AutoCreate `/indexing/evaluation/*` endpoints.
- `SuggestedQuestionsStep.tsx` — POSTs to `/followups/init` and later reads `/followups/results` to display follow-up ideas, with inline editing and approval.
- `TranslationStep.tsx` — manages translation jobs (`/i18n/*`) and per-language confirmation state, storing edits back into AutoCreate’s storage.
- `FinalJsonGenerationStep.tsx` — performs Step 7.5 exports (`/step8/export-questions-with-answers`, `/step8/fill-placeholders`) and exposes inline JSON editors.
- `GithubSyncStep.tsx` — Step 8 actions (activate country, adjust landing page, upload logos, sync to GitHub). It also includes placeholder buttons for “Upload manifestos to backend” and “Create backend routes/country setup” where the ElectOMate CRUD calls will be wired in.
- `BatchAddQuestions.tsx`, `NewCountryEvaluationResults.css`, and `NewCountryPage.css` — UI helpers and styling.

The main component stores wizard progress under `workflow_state` by calling AutoCreate `/new-country/drafts/{code}/workflow-state`. That state feeds the progress indicators and ensures the user can resume tasks.

## AutoCreate Backend & Storage Interop

The AutoCreate FastAPI app (referenced in the repo as “AutoCreate backend”) proxies all wizard actions. Important modules:

- `new_country_routes.py` — exposes REST endpoints under `http://localhost:8001/new-country/…`. High-level flow:
  - `discover-and-logos/*` launches Perplexity-based discovery, writes interim data into storage, and returns readiness status.
  - `drafts/*` endpoints manage persisted drafts: initialise, list, load, update parties, upload assets, and coordinate QGen/indexing/follow-up jobs.
  - `step8/*` endpoints (activate country, adjust landing JSON, setup languages, GitHub sync) manipulate frontend repo files before pushing commits.
  - When integrating ElectOMate CRUD, this file is where we’ll inject calls to the `/v2` routes (e.g., after confirming parties, call `POST /v2/parties/`).

- `storage.py` — implements disk persistence under `AutoCreate/AAA_New_Countries_Storage/{COUNTRY_CODE}/`. It manages:
  - Unique country code generation (`generate_unique_country_code`) and file structure creation.
  - `save_parties_json` / `load_parties_json` — read/write `PartiesJson.json`, the canonical source for parties, base languages, and metadata used later by the frontend.
  - Asset helpers (`update_party_logo`, `upload_manifesto`, etc.) that copy uploads into `country-storage/{code}/…` and update JSON metadata.
  - `update_workflow_*` functions to mutate `workflow_state.json`, tracking which step is complete.

The stored JSON files drive multiple steps:

- `PartiesJson.json` — contains election details, party list (including `shortname` / `party_short_name`), manifesto file references, and base languages. This file should remain the single truth that both AutoCreate and ElectOMate use to build consistent party shortnames.
- `questions.json`, `nested_chunks.json`, `evals_db_total.json`, `step6_suggested_followups_for_user.json`, etc. — produced as each step completes so that users can resume or regenerate without re-running all LLM calls.

### Planned Integration Points

To connect AutoCreate with ElectOMate:

1. **Country/Election creation** — after the wizard confirms a country/election in `NewCountryPage.tsx`, add an AutoCreate route that calls `POST /v2/countries/` and `POST /v2/elections/`, storing the returned UUIDs inside `PartiesJson.json` or `workflow_state`.
2. **Party creation** — once the user locks their party list (Step 2), call `POST /v2/parties/` for each entry. Persist the `id` for later document uploads.
3. **Manifesto ingestion** — after uploading PDFs to AutoCreate, call ElectOMate `/v2/documents/` with the stored `party_id`. When the backend finishes parsing, Weaviate indexes the content automatically.
4. **Candidate information** — optional step to mirror candidate details into `/v2/candidates/` when present in `PartiesJson.json`.

By caching ElectOMate UUIDs alongside AutoCreate metadata, the chat frontend can issue `/v2/agent/chat` calls with consistent `election_id` and party shortnames, guaranteeing that Weaviate queries return the correct manifesto chunks.


