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
- [ ] Frontend: Benchmark run page with real-time charts
- [ ] Health timeline (concurrency vs latency percentiles)
- [ ] Per-profile latency breakdown
- [ ] Throughput gauge (tokens/sec, requests/sec)
- [ ] Error rate indicator
- [ ] Active sessions / turns counter
- [ ] Auto-scroll request log

## Phase 7: Results & Response Browser
- [ ] Frontend: Results summary page (post-run analysis)
- [ ] Latency distribution histogram
- [ ] Per-profile performance comparison
- [ ] Response browser (browse full conversations, filter, sort)
- [ ] Quality flags (truncated, empty, refusal, repeated tokens)
- [ ] Benchmark comparison mode (overlay two runs)
- [ ] Export (CSV/JSON)

## Phase 8: Load Curves & Breaking Point Detection
- [ ] Load curve visualization in scenario builder
- [ ] Step / ramp / spike / wave curve implementations
- [ ] Breaking point auto-detection (latency spike, error threshold)
- [ ] Breaking point marker on dashboard timeline

## Phase 9: Polish
- [ ] Cost estimation (user-provided $/token rate)
- [ ] Error categorization (timeout, rate limit, malformed, refusal)
- [ ] Endpoint quick-test UI (send one request, see raw response)
- [ ] Responsive layout refinements
- [ ] Loading states and empty states
- [ ] Documentation
