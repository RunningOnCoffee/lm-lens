# LM Lens — Project Instructions

## What is LM Lens?
An open-source LLM performance benchmarking tool that simulates realistic multi-user workloads against any OpenAI-compatible API endpoint. Docker Compose stack with three services: FastAPI backend, React frontend, PostgreSQL database.

## Development Workflow — MANDATORY
1. **Work in small phases.** Each phase must be fully working before moving to the next.
2. **Test plan first.** Before marking a phase complete, write a concrete test plan for the user.
3. **User confirms.** Do NOT proceed to the next phase until the user has tested and confirmed it works.
4. **Fix before moving on.** If tests fail, fix the issue in the current phase. Never carry broken code forward.
5. **Git commit per phase.** Commit after each phase passes testing. This gives rollback points.
6. **Tests alongside code.** Each backend phase includes pytest tests that exercise the new functionality.
7. **Update PROGRESS.md.** Check off items as they're completed so the file always reflects current state.

## Architecture

### Services
| Service | Tech | Port (host) | Port (container) |
|---------|------|-------------|-------------------|
| `lm-lens-api` | Python 3.12, FastAPI, SQLAlchemy 2.0 async (asyncpg) | 8080 | 8000 |
| `lm-lens-ui` | React 18, Vite 5, Tailwind CSS 3, Nginx | 8090 | 80 |
| `lm-lens-db` | PostgreSQL 16 | 5433 | 5432 |
| `lm-lens-mock` | FastAPI mock OpenAI API (optional, for testing) | 8081 | 8000 |

### Key Design Decisions
- **No authentication** — LM Lens is a local development/benchmarking tool, not a multi-tenant SaaS. API keys are stored in the DB but the tool itself runs on localhost.
- **Nginx reverse proxy** — Frontend Nginx proxies `/api/` to backend, eliminating CORS issues.
- **WebSocket for live metrics** — Backend pre-aggregates metrics every 1s, pushes snapshots via WS.
- **Async everything** — `asyncio.Semaphore` for concurrency control, `httpx.AsyncClient` for LLM calls, `asyncpg` for DB.
- **Batch metric writes** — Buffer in memory, flush to Postgres every 100 records or 1 second.

### Database
- Connection: `postgresql+asyncpg://lm-lens:lm-lens@lm-lens-db:5432/lm-lens`
- Alembic for migrations, auto-run on startup via entrypoint.sh
- JSONB columns for flexible metadata (prompt templates, scenario configs, LLM response data)
- Indexes on (benchmark_id, timestamp) and (benchmark_id, profile_id) for analytical queries

### Frontend Design
- Industrial dark theme: `#0d0f14` background, `#00d4ff` (electric cyan) primary accent
- Fonts: JetBrains Mono (data/monospace), Outfit (headings)
- Amber for warnings, red for errors
- Recharts for standard charts; canvas-based rendering for high-density plots (deferred to polish phase)
- TanStack Table v8 for data tables
- Zustand for state management
- React Router v6

## Code Conventions

### Backend (Python)
- Type hints on all functions
- Pydantic models for all API request/response schemas
- Async SQLAlchemy 2.0 style (use `async_session`, `select()`, etc.)
- Router files in `app/routers/`, business logic in `app/services/`
- Engine code (benchmark runner, simulator, LLM client) in `app/engine/`
- All timestamps UTC, durations in milliseconds internally

### Frontend (React/JS)
- Functional components with hooks
- Zustand stores in `src/stores/`
- API client functions in `src/api/`
- Pages in `src/pages/`, reusable components in `src/components/`
- Tailwind for styling, no CSS modules

### API Response Envelope
All API responses follow a consistent format:
```json
// Single item
{"data": {...}}

// List with pagination
{"data": [...], "meta": {"total": 42, "page": 1, "per_page": 20}}

// Error
{"error": {"message": "...", "code": "NOT_FOUND"}}
```

### Docker
- Multi-stage builds for small final images
- Backend entrypoint: wait for Postgres → run Alembic → start uvicorn
- All config via environment variables with sensible defaults
- `.env` file for local development

### Database Seeding
- Built-in profiles have a `slug` field (e.g., `casual-user`) used as stable identifier
- Seed uses upsert logic: insert if slug missing, update if exists — allows updating built-in prompts across versions
- Never creates duplicates on restart

### Commands (lens.bat)
```
lens up        — docker compose up --build -d
lens down      — docker compose down
lens logs      — docker compose logs -f
lens test      — docker compose exec lm-lens-api pytest
lens db-shell  — connect to Postgres via psql
lens reset     — docker compose down -v && docker compose up --build -d
```
Or just run the `docker compose` commands directly.

## File Structure
```
lm-lens/
├── docker-compose.yml
├── .env.example
├── .env
├── CLAUDE.md              # This file
├── PROGRESS.md            # Phase tracker
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── engine/
│   │   ├── services/
│   │   └── seed_data/
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── api/
│       └── stores/
└── docs/
```

## API Endpoints
```
POST   /api/v1/benchmarks              — Start a new benchmark run
GET    /api/v1/benchmarks              — List all runs
GET    /api/v1/benchmarks/{id}         — Get run details + results
DELETE /api/v1/benchmarks/{id}         — Delete a run
POST   /api/v1/benchmarks/{id}/abort   — Abort a running benchmark
WS     /api/v1/benchmarks/{id}/live    — WebSocket for live metrics

GET    /api/v1/profiles                — List all templates
POST   /api/v1/profiles                — Create custom template
GET    /api/v1/profiles/{id}           — Get template details
PUT    /api/v1/profiles/{id}           — Update template
DELETE /api/v1/profiles/{id}           — Delete custom template
POST   /api/v1/profiles/{id}/clone     — Clone a template

GET    /api/v1/scenarios               — List saved scenarios
POST   /api/v1/scenarios               — Save a scenario
GET    /api/v1/scenarios/{id}          — Get scenario details
PUT    /api/v1/scenarios/{id}          — Update scenario
DELETE /api/v1/scenarios/{id}          — Delete scenario
POST   /api/v1/scenarios/{id}/clone    — Clone a scenario

GET    /api/v1/health                  — Health check
POST   /api/v1/endpoint/test           — Test LLM endpoint connectivity
GET    /api/v1/export/{benchmark_id}   — Export results as CSV/JSON
```

## Built-in User Profile Templates (7)
1. Casual User — Short conversational prompts, 1-3 turn sessions
2. Power User / Researcher — Long analytical prompts, 5-15 turns
3. Programmer — Code snippets, debugging, multi-turn refinement
4. Content Creator / Marketing — Document rewrites, summaries, SEO
5. Data Analyst — CSV/table data, SQL generation, analysis
6. Customer Support Bot — Short queries, structured responses
7. RAG Pipeline Simulator — Large context blocks, long-context testing

## Metrics Collected Per Request
TTFT, TGT, ITL, input/output tokens, TPS, HTTP status, error details, user profile, session ID, turn number, timestamp, model reported

## Connecting to LLM Endpoints

LM Lens benchmarks any OpenAI-compatible API. Since requests are made from the **backend Docker container**, the endpoint URL must be reachable from inside Docker.

| LLM Location | Endpoint URL |
|---|---|
| Built-in mock server | `http://lm-lens-mock:8000` |
| Local LLM on host (llama.cpp, vLLM, Ollama, LM Studio) | `http://host.docker.internal:PORT` |
| LLM on another machine on the network (e.g., DGX Spark) | `http://<MACHINE_IP>:PORT` |
| Cloud API (OpenAI, Together, etc.) | `https://api.openai.com` (+ API key) |

The `/v1/chat/completions` path is appended automatically if not present. Use **Test Connection** in the Scenario Editor to verify connectivity.

### Example: llama.cpp on a remote machine
If llama-server is running on a DGX Spark at `192.168.1.50:8080`:
- Endpoint URL: `http://192.168.1.50:8080`
- Model Name: check `http://192.168.1.50:8080/v1/models` for the loaded model name
- API Key: leave empty (llama.cpp default)

## Scenario Test Modes
- **Stress Test** — All virtual users active simultaneously for the full duration
- **Ramp Up** — Gradually add users over time (configurable step size and interval)
- **Breaking Point** — Ramp up until failure criteria are breached (TTFT, inter-token latency, error rate thresholds)

## Safety Rails
- Max concurrency cap (configurable, default 100) to prevent accidental DDoS
- Graceful abort — preserves all data collected so far
- Error capture as data, not crashes
- Connection timeout defaults (30s connect, 120s read)
