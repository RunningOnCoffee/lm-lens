# LM Lens — Progress Tracker

## Phase 1: Infrastructure
- [x] Docker Compose (backend, frontend, database, mock LLM server)
- [x] PostgreSQL 16 setup with asyncpg
- [x] FastAPI backend skeleton (config, database, health check)
- [x] Alembic migrations setup + entrypoint script
- [x] React + Vite + Tailwind frontend skeleton
- [x] Nginx reverse proxy config (frontend proxies /api/ to backend)
- [x] Mock LLM server (OpenAI-compatible, configurable latency + streaming)
- [x] lens.bat convenience commands (replaced Makefile)
- [x] .env setup

## Phase 2: Prompt Data Model & Seed Data
- [x] Database models (profiles, conversation_templates, follow_up_prompts, template_variables, code_snippets)
- [x] Alembic migration for all tables
- [x] Pydantic schemas for all models
- [x] Seed data: 7 built-in profiles with starter prompts, follow-ups, variables, code snippets
- [x] Seed runner (upsert on startup via slug)
- [x] Profiles list + detail API endpoints
- [x] Pytest tests for models and seed

## Phase 3: Profile & Prompt Management API + UI
- [x] CRUD API for profiles (create, update, delete, clone with auto-numbered names)
- [x] Conversation preview endpoint (generate a sample conversation)
- [x] Frontend: Profile list page (two-table layout, multi-select, bulk actions)
- [x] Frontend: Profile editor (create/edit/clone with prompt management)
- [x] Frontend: Profile view page (read-only for built-in profiles)
- [x] Frontend: Conversation preview panel
- [x] Variable syntax: $VAR_NAME (uppercase, alphanumeric), replaces {{var_name}}
- [x] Editor UX: info tooltips, single-shot fades turns, min/max labels + validation
- [x] Editor UX: individual variable value entry (textarea per value, supports long content)
- [x] Editor UX: save stays on page with success feedback, back button
- [x] Token range fields removed from template editor (will be scenario-level LLM params in Phase 5)
- [x] Pytest tests for CRUD endpoints (13 tests passing)

## Phase 4: Scenario Builder API + UI
- [x] Database models (scenarios, scenario_profiles with user_count instead of weight)
- [x] Alembic migration 003_scenario_tables
- [x] Pydantic schemas (LLMParams, LoadConfig, BreakingCriteria, ScenarioCreate/Read/Update/Summary, EndpointTest)
- [x] CRUD API for scenarios (list, get, create, update, delete, clone)
- [x] Endpoint test API (POST /api/v1/endpoint/test)
- [x] Frontend: Scenario list page (profiles, model, users, mode, duration columns)
- [x] Frontend: Scenario builder — endpoint config with helper text for local LLMs
- [x] Frontend: LLM params with info tooltips, optional max_tokens (empty = no limit), proper ranges
- [x] Frontend: Profile mix with absolute user counts (+/- buttons, auto-calculated percentages)
- [x] Frontend: Test modes — Stress Test, Ramp Up, Breaking Point with failure criteria (TTFT, ITL, error rate)
- [x] Frontend: Save button animation (green flash + "Saved!" feedback)
- [x] Pytest tests for scenario endpoints (12 tests, 25 total passing)

## Phase 5: Benchmark Engine
- [x] Database models (benchmarks, benchmark_requests, benchmark_snapshots)
- [x] Alembic migration 004_benchmark_tables
- [x] Pydantic schemas (BenchmarkCreate/Read/Summary, BenchmarkRequestRead, BenchmarkSnapshotRead)
- [x] LLM client (httpx async, streaming SSE + non-streaming, TTFT/ITL/TGT measurement, error classification)
- [x] Metric collector (async buffer, batch flush to Postgres every 1s or 100 records)
- [x] Snapshot generator (1s aggregation, percentile computation, per-profile breakdown)
- [x] WebSocket manager (singleton, per-benchmark connections, broadcast from snapshot generator)
- [x] Conversation simulator (multi-turn, think time, read time, variable substitution, interruptible sleep, abort support)
- [x] Benchmark runner (stress/ramp/breaking_point modes, asyncio.Semaphore concurrency control, results summary computation)
- [x] Benchmark lifecycle API (POST start, GET list, GET detail, DELETE, POST abort)
- [x] WebSocket endpoint (WS /api/v1/benchmarks/{id}/live)
- [x] Frontend API stub (benchmarksApi in client.js)
- [x] Pytest tests for engine components (27 new tests, 52 total passing)

## Phase 6: Live Dashboard
- [x] Frontend: Benchmark list page (start, abort, delete, scenario picker, status polling)
- [x] Frontend: Benchmark run page with real-time metric cards (live + summary modes)
- [x] WebSocket hook with reconnect, benchmark Zustand store
- [x] Backend: cumulative metrics in WebSocket snapshots, elapsed_seconds timing
- [x] Backend: GET /benchmarks/{id}/snapshots endpoint with computed elapsed_seconds
- [x] Health timeline (TTFT p50/p95/p99 over time + active users overlay)
- [x] Per-profile latency breakdown (bar chart, p50/p95 TTFT per profile)
- [x] Throughput chart (tokens/sec area + min tok/s + requests/sec)
- [x] Error rate chart (errors over time, green "no errors" state)
- [x] Countdown timer + progress bar during active runs
- [x] Status badges, abort button, live indicator
- [x] Auto-scroll request log

## Phase 6.5: AI Endpoints Refactor
- [x] New `endpoints` table (name, URL, API key, model, GPU, inference engine, notes)
- [x] Endpoint model, schemas, Alembic migration 005
- [x] Endpoints CRUD router (list, get, create, update, delete, clone, test connection)
- [x] Remove endpoint fields from scenarios (model, schema, router, frontend)
- [x] Benchmark creation takes scenario_id + endpoint_id, stores endpoint_snapshot
- [x] BenchmarkRunner reads endpoint config from endpoint_snapshot
- [x] Frontend: AI Endpoints sidebar tab + list page + editor page
- [x] Frontend: Endpoint picker on benchmark start (scenario + endpoint dropdowns)
- [x] Frontend: Endpoint info badges on benchmark run page (name, model, GPU, engine)
- [x] Frontend: Endpoint name/model shown in benchmark list

## Phase 7: Results & Response Browser

### 7a: Backend Foundation (complete)
- [x] Quality flags JSONB column + Alembic migration 006
- [x] Quality flag detection at write time (empty, truncated, refusal, repeated_tokens)
- [x] finish_reason capture in LLM client (streaming + non-streaming)
- [x] Paginated GET /requests with filters (profile, turn, error, quality_flag, success, session) and sorting
- [x] GET /histogram endpoint (server-side bin computation, p50/p95/p99/mean stats)
- [x] GET /profile-stats endpoint (per-profile aggregated stats + quality flag counts)
- [x] GET /compare endpoint (side-by-side benchmark comparison)
- [x] GET /export endpoint (CSV streaming + JSON download)
- [x] Quality flag counts in _compute_summary
- [x] Pytest tests for all new endpoints (21 total)

### 7b: Tab Navigation + Analysis Tab (complete)
- [x] Tab bar component (Overview | Analysis | Responses) for completed/aborted/failed runs
- [x] Latency histogram chart (Recharts BarChart, metric selector, profile filter, p50/p95/p99 reference lines)
- [x] Per-profile comparison chart (grouped bars TTFT p50/p95) + stats table with quality flags
- [x] Shared InfoTip component (portal-based tooltips, positioned above icon)
- [x] InfoTip tooltips on all metric acronyms (TTFT, TGT, P50, P95, tok/s) across all pages
- [x] Abort button immediate "Aborting…" feedback
- [x] RequestLog field normalization for Phase 7a schema changes
- [x] Bulk delete on benchmarks list view

### 7c: Response Browser (complete)
- [x] GET /sessions endpoint (session-level aggregates with pagination, profile filter)
- [x] Session-grouped conversation list with summary stats (profile, turns, TTFT, tok/s, tokens, flags)
- [x] Chat-style conversation view (user prompt + LLM response bubbles, turn by turn)
- [x] Expandable turn details (metrics, request body JSON, ITL sparkline)
- [x] Quality flag pills (colored: amber=truncated, gray=empty, red=refusal, purple=repeated)
- [x] Profile filter, session pagination

### 7d: Export UI (complete)
- [x] Export dropdown on BenchmarkRun header (CSV / JSON download)
- [x] Accent-colored button with loading state

### 7e: Benchmark Comparison Mode (complete)
- [x] BenchmarkCompare page (side-by-side run info, key metrics table with delta %, per-profile breakdown)
- [x] Delta badges with color coding (green = better, red = worse, context-aware for latency vs throughput)
- [x] Multi-select exactly 2 benchmarks → Compare button on bulk action bar
- [x] Route: /benchmarks/compare?a={id}&b={id}

### 7f: Polish
- [ ] Quality flag counts on Overview tab
- [ ] finish_reason end-to-end verification with mock server
- [ ] Final visual polish

## Phase 8: Load Curves & Breaking Point Detection
- [ ] Load curve visualization in scenario builder
- [ ] Step / ramp / spike / wave curve implementations
- [ ] Breaking point auto-detection (latency spike, error threshold)
- [ ] Breaking point marker on dashboard timeline

## Phase 9: Polish
- [ ] Cost estimation (user-provided $/token rate)
- [ ] Error categorization (timeout, rate limit, malformed, refusal)
- [ ] Endpoint quick-test UI (send one request, see raw response)
- [ ] Expected throughput estimate in scenario builder (warn when think_time × users × duration yields very few requests)
- [ ] Responsive layout refinements
- [ ] Loading states and empty states
- [ ] Documentation
