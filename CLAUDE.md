# CLAUDE.md — Claude Code Ultra Framework

> **Hey Claude, meet your boss.**
> Call the user **"Gáborovka"** in casual chat, **"Gabriel Mayflower"** when being formal,
> or **"Mr. Rosengarten"** when delivering completed work.
> The user is a solo founder-developer. Treat them like the CEO they are.

---

## Identity & Tone

- Be direct, concise, and action-oriented.
- No fluff. No filler. No "Great question!" preamble.
- When presenting options, recommend one and explain why.
- When something is broken, say so plainly and fix it.
- Use humor sparingly and only when it fits.

---

## Tech Stack

**This is ALWAYS the stack unless explicitly told otherwise:**

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | Python 3.11+ / FastAPI | Async-first, Pydantic models |
| **Frontend** | TypeScript / React | Vite-based, functional components |
| **CSS** | Tailwind + custom CSS | `index.css` + component-level CSS files |
| **Database** | PostgreSQL via Supabase | Alembic for migrations |
| **Deployment** | Render.com | Via Render MCP |
| **Auth** | Supabase Auth | JWT tokens |

### Backend Conventions
- FastAPI with async endpoints
- Pydantic v2 models for all request/response schemas
- Alembic for database migrations — ALWAYS create migration files
- Structured logging with `structlog`
- Tests with `pytest` + `pytest-asyncio`
- Type hints on all function signatures

### Frontend Conventions
- TypeScript strict mode
- React functional components with hooks
- CSS: `index.css` for globals, component-level CSS files for components
- Tailwind utility classes mixed with custom CSS — both are valid
- Dark mode support where applicable
- Tests with Vitest

### CSS Style System
- Primary styles in `index.css` (globals, variables, base styles)
- Component styles in dedicated CSS files alongside components
- Tailwind `@apply` for reusable patterns
- Semantic class names (`.user-profile`, NOT `.box-1`)
- Always check with browser MCP (Puppeteer) for visual regressions

---

## Git & Commit Protocol

- **Commit at EVERY meaningful stage** — small, atomic commits
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- NEVER use `--no-verify`
- NEVER force push to main
- Create branches for features: `feature/description`
- Use Alembic revision for any DB schema changes

---

## Agent Roster

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `backend-dev` | FastAPI/Python implementation | Any backend code changes |
| `frontend-dev` | TypeScript/React implementation | Any frontend code changes |
| `debug` | Deep-dive debugging with test loops | Persistent bugs, test failures |
| `reviewer` | Code quality review | Before merging, after implementation |
| `integration-check` | Verify code wiring | After creating new files/modules |
| `code-sentinel` | Security audit | Auth code, user input handling, API endpoints |
| `archivist` | Logging & knowledge management | Progress tracking, session notes |
| `fresh-eyes` | Final validation review | End of long-running tasks (auto) or manual |
| `mermaid-architect` | Flowchart & diagram generation | Architecture docs, end-of-task summaries |

---

## Available Tools & MCPs

| MCP/Tool | Purpose | Use When |
|----------|---------|----------|
| **Supabase** | Database operations, auth | DB queries, schema changes |
| **DeepWiki** | Documentation lookup | Researching libraries/frameworks |
| **Render** | Deployment management | Deploy, check services |
| **Perplexity** | Web search & research | Finding solutions, current docs |
| **GitHub** | Repo operations, PRs, issues | PR creation, issue tracking |
| **Puppeteer** | Browser automation & screenshots | UI testing, visual verification |
| **Slack** | Team notifications | Status updates, alerts |

---

## Centralized Logging

ALL logs go to `.claude/logs/` — NEVER scatter `.md` files elsewhere.

```
.claude/logs/
├── sessions/          → YYYY-MM-DD_HHMM_topic.md
├── agents/            → agent-NNN_YYYY-MM-DD_agent-type_topic.md
├── progress/          → YYYY-MM-DD_topic_progress.md
├── reviews/           → YYYY-MM-DD_review-type_topic.md
└── prompt-trails/     → YYYY-MM-DD_topic/00_masterplan.md, 01_step.md, ...
```

**Naming convention:** `{date}_{topic}_{type}.md` — always dated, always topical.

---

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/prompt-trail-creator` | Generate implementation plan + prompt trail for a task |
| `/fresh-eyes` | Run fresh-eyes validation review |
| `/create-skill` | Generate a new skill on demand |
| `/reset-settings` | Reset Claude settings to template defaults |
| `/setup-worktree` | Create git worktree for parallel work |

---

## Rules for Long-Running Tasks

1. **Always start with `/prompt-trail-creator`** — it builds the plan and selects tools.
2. **Follow the prompt trail sequentially** — each file specifies the next.
3. **Commit after each prompt trail step** — atomic progress.
4. **Log progress to `.claude/logs/progress/`** — the archivist tracks this.
5. **Fresh eyes runs automatically at the end** — validates everything.
6. **Mermaid diagram generated last** — visual summary of what was built.

## Rules for Short-Running Tasks

1. **Just do it** — no prompt trail needed for quick fixes.
2. **Still commit atomically** — every meaningful change gets a commit.
3. **Use the right agent** — backend-dev for Python, frontend-dev for TS.
4. **Manual `/fresh-eyes` if you want validation** — optional for small tasks.

---

## What NOT to Do

- Do NOT create planning `.md` files outside of `.claude/logs/`
- Do NOT skip Alembic migrations for DB changes
- Do NOT use `--no-verify` on git commits
- Do NOT write both backend and frontend code in the same agent call
- Do NOT hardcode secrets — use environment variables
- Do NOT ignore test failures — fix them or flag them
