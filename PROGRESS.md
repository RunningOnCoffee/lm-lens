# LM Lens — Progress Tracker

## Phase 1: Infrastructure
- [x] Docker Compose (backend, frontend, database, mock LLM server)
- [x] PostgreSQL 16 setup with asyncpg
- [x] FastAPI backend skeleton (config, database, health check)
- [x] Alembic migrations setup + entrypoint script
- [x] React + Vite + Tailwind frontend skeleton
- [x] Nginx reverse proxy config (frontend proxies /api/ to backend)
- [x] Mock LLM server (OpenAI-compatible, configurable latency + streaming)
- [x] Docker Compose commands documented in CLAUDE.md
- [x] .env setup

## Phase 2: Prompt Data Model & Seed Data
- [x] Database models (profiles, conversation_templates, follow_up_prompts, template_variables, code_snippets)
- [x] Alembic migration for all tables
- [x] Pydantic schemas for all models
- [x] Seed data: 7 built-in profiles with starter prompts, follow-ups, variables, code snippets
- [x] Seed runner (insert-if-missing on startup via slug, edits preserved)
- [x] Profiles list + detail API endpoints
- [x] Pytest tests for models and seed

## Phase 3: Profile & Prompt Management API + UI
- [x] CRUD API for profiles (create, update, delete, clone with auto-numbered names)
- [x] Conversation preview endpoint (generate a sample conversation)
- [x] Frontend: Profile list page (two-table layout, multi-select, bulk actions)
- [x] Frontend: Profile editor (create/edit/clone with prompt management)
- [x] Frontend: Profile editor (built-in profiles editable with Reset to Defaults)
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

### 7e Fixes: Seeded Benchmark Bugs
- [x] Deterministic snapshot ordering (sorted relationships + order_by on models)
- [x] Seeded multi-turn conversation history accumulation
- [x] Request body stores message snapshot, not mutable reference
- [x] Comparison responses show per-side prompts for non-seeded runs
- [x] maxTurns based on actual requests, not prompt plan length

### 7f: Polish
- [x] Quality flag counts on Overview tab (colored pills with counts, only shown when flags exist)
- [x] finish_reason end-to-end verification with mock server (mock respects max_tokens, returns "length")
- [x] Seed input InfoTip tooltip (replaced browser title attribute)
- [x] Save button in header of Profile and Scenario editors (no scrolling needed)
- [x] Auto-generated 4-digit seed when user doesn't provide one (always reproducible)
- [x] Built-in profiles are editable with "Reset to Defaults" button
- [x] Seed runner only creates profiles that don't exist (user edits survive restarts)
- [x] POST /profiles/{id}/reset endpoint for built-in profile restoration
- [x] Removed lens.bat (docker compose commands documented in CLAUDE.md)
- [ ] Final visual polish (loading states, empty states, error handling — see audit notes below)

### Visual Polish Audit (deferred to Phase 10)
Identified but not yet implemented:
- Reusable Spinner component (replace 6+ text-only loading states)
- RequestLog returns null when empty (should show placeholder card)
- Silent API error handling (.catch(() => {})) across multiple components
- Delete confirmation auto-dismiss timeout
- Chart empty states (LatencyTimeline, ThroughputChart)
- Response truncation UX (silent 800/2000 char cuts, no expand option)
- Success feedback on delete/export actions

## Phase 8: Load Curves, Breaking Point & Quality-Under-Load
- [x] Load curve engine: Step, Linear, Spike, Wave implementations (backend)
- [x] Load curve visualization + preview chart in scenario builder (frontend)
- [x] Enhanced quality flags (JSON validity, format compliance, length compliance, language detection)
- [x] Quality flag counts tracked in snapshots + WebSocket broadcast
- [x] Breaking point auto-detection (latency spike, error threshold, ITL)
- [x] Breaking point details recorded in results_summary (elapsed, users, reason)
- [x] Breaking point marker on dashboard timeline (red dashed line with label)
- [x] Quality-under-load correlation chart (quality flag rates overlaid on concurrency timeline)

## Phase 9: A/B Quality Comparison
- [x] Quality scoring engine (4 dimensions: completeness, compliance, coherence, safety)
- [x] Per-request quality_scores JSONB column + Alembic migration 009
- [x] Quality scores API endpoint (GET /benchmarks/{id}/quality-scores)
- [x] Enhanced /compare endpoint with quality_comparison (per-dimension delta + overall winner)
- [x] Quality Scorecard UI on Overview tab (overall score, dimension bars, flag distribution, per-profile table)
- [x] Quality comparison UI (winner banner, dimension side-by-side bars, flag diff)
- [x] Aborted requests excluded from quality scoring
- [x] Profile refinement: reduced from 11 to 4 built-in profiles (Casual User, Power User, Programmer, Data Analyst)
- [x] Programmer profile: real code snippets replacing $CODE_BLOCK placeholder
- [x] Test cleanup: ID-tracking in conftest.py, no leftover data

## Phase 9 Bug Fixes
- [x] Seeded benchmarks: looping users now get varied prompts after first seeded session (templates + variables populated on seeded SessionConfig, seeded_prompts cleared after first run)

## Phase 10: Polish & Improvements

### 10e: Concurrent Benchmark Warning (complete)
- [x] Frontend warns when starting a benchmark on an endpoint already under load
- [x] Confirmation dialog with conflict details, "Run Anyway" option
- [x] Abort button immediately shows "Aborting..." and disables
- [x] Actions column widened to prevent layout shift

### 10a: Improved Heuristic Detection (complete)
- [x] N-gram text repetition detection (5-gram >30% positions, or same sentence 3+ times)
- [x] Reduced refusal false positives (first 300 chars only, negative patterns like "I cannot stress")
- [x] Responsiveness dimension evaluated and removed — keyword overlap too crude to be meaningful

### Dashboard Redesign (complete)
- [x] Backend: GET /api/v1/dashboard — fleet overview, per-endpoint performance, per-profile latency, recent runs
- [x] Backend: GET /api/v1/dashboard/token-economy — token breakdown by endpoint or profile
- [x] Backend: planned_duration on BenchmarkSummary, total_input/output_tokens on ProfileStatsEntry
- [x] Frontend: Fleet overview metric cards (benchmarks, requests, tokens, quality)
- [x] Frontend: Endpoint performance table (TTFT, tok/s, quality, tokens, last run)
- [x] Frontend: TTFT by Endpoint bar chart
- [x] Frontend: Token Economy chart (by profile / by endpoint toggle)
- [x] Frontend: Profile Latency horizontal bar chart
- [x] Frontend: Quality by Endpoint progress bars
- [x] Frontend: Live benchmarks in Recent Runs with elapsed/planned timer, auto-refresh on completion
- [x] Frontend: Extracted MetricCard and StatusBadge to shared components
- [x] 133 tests passing

### Remaining
- [ ] Phase D: Per-run token economy chart on BenchmarkRun Analysis tab
- [ ] Phase 10f/10g: Live quality scores via WebSocket + live QualityScorecard widget
- [ ] Phase 10b-10d: LLM-as-Judge (data model, engine, frontend)
- [ ] Visual polish items from audit (loading states, empty states, error handling)
- [ ] Documentation / README
