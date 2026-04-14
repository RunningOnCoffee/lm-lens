# Session Handoff — Phase 10 Plan Ready

## Current State (2026-04-13)

Phase 9 (A/B Quality Comparison) is **complete and committed** (`fe72270`). Seeded prompt variety bug is **fixed**. 129 tests passing. Phase 10 has been planned but not started.

---

## Phase 10 Implementation Plan

Three workstreams, 7 phases. Ordered for fast early wins (small phases first, migrations last).

### Workstream 1: Quality Assessment Improvements + LLM-as-Judge

#### Phase 10a: Improved Heuristic Detection (no schema changes)

**1. Better repeated-tokens detection — add N-gram text analysis**
- New helper `_check_text_repetition(response: str) -> bool` in `collector.py`
- Extract 5-grams, flag if any single 5-gram appears in >30% of positions
- Also check sentence-level: same sentence 3+ times = flag
- Skip for responses under 100 chars
- OR with existing ITL-based check (either triggers `repeated_tokens`)

**2. Reduced refusal false positives**
- Apply `_REFUSAL_PATTERNS` only to first 300 chars of response (refusals are always up front)
- Add negative lookahead: "I cannot stress", "I cannot overstate", "I can't help but", "I cannot emphasize"
- Add new patterns: "I'm sorry, but I'm not able", "my guidelines prevent", "it would be inappropriate"

**3. New `responsiveness` dimension — does the response address the prompt?**
- New helper `_check_responsiveness(prompt: str, response: str) -> bool` in `collector.py`
- Extract keywords from prompt (words >4 chars, skip common stop words)
- If prompt has 3+ keywords and zero appear in response, flag as `unresponsive`
- Conservative: only catches clear mismatches
- `quality_scorer.py`: add dimension, rebalance weights to completeness 25%, compliance 25%, coherence 15%, responsiveness 15%, safety 20%
- `QualityScorecard.jsx`: add responsiveness to `DIMENSION_META` and `DIMENSION_ORDER`
- `BenchmarkCompare.jsx`: add responsiveness to dimension comparison
- No migration needed (JSONB columns flex with new keys)

**Files**: `collector.py`, `quality_scorer.py`, `QualityScorecard.jsx`, `BenchmarkCompare.jsx`
**Tests**: Unit tests for each new/modified detection function + scorer weight changes

---

#### Phase 10b: LLM-as-Judge Data Model + Settings

**1. App settings table**
- New model `backend/app/models/settings.py`: `AppSetting` (key: str PK, value: JSONB)
- Migration `010_app_settings.py`
- Judge config stored as key `"judge_endpoint"`, value `{"endpoint_id": "uuid", "enabled": true, "max_concurrent": 5, "timeout_seconds": 30}`

**2. Judge score columns on BenchmarkRequest**
- Add `judge_scores: JSONB | None` and `judge_status: str | None` ("pending"/"completed"/"failed"/"skipped")
- Migration `011_judge_scores.py`

**3. Settings API**
- New router `backend/app/routers/settings.py`
- `GET /api/v1/settings/judge` — return current judge config
- `PUT /api/v1/settings/judge` — update (validates endpoint_id exists)
- Register in `main.py`

**4. Frontend settings page**
- New `frontend/src/pages/Settings.jsx` — Judge Endpoint config
- Dropdown to pick from existing endpoints, enable/disable toggle, concurrency + timeout fields
- Add Settings to sidebar nav

**Design decision**: Judge endpoint is a **global setting** (not per-scenario). Rationale: it's infrastructure (which model to trust as judge), not test design.

---

#### Phase 10c: LLM-as-Judge Engine

**Design decision**: Runs **post-completion** (batch mode), not during the benchmark. Rationale:
- During benchmark, the target endpoint is under load — judge calls add noise
- Batch is simpler, can be retried without re-running the benchmark
- Judge failures don't create confusing partial states

**1. Judge runner** — new `backend/app/engine/judge.py`
- `JudgeRunner(benchmark_id, judge_endpoint_snapshot, session_factory, max_concurrent, timeout)`
- Loads all BenchmarkRequest rows with response_text
- For each: sends original prompt + response to judge via structured prompt
- Judge rates: relevance (0-10), helpfulness (0-10), accuracy (0-10), depth (0-10)
- Normalizes to 0.0-1.0, stores in `judge_scores` JSONB, sets `judge_status`
- `asyncio.Semaphore(max_concurrent)` for rate control
- Per-request error handling: timeout/parse failure → `judge_status="failed"`, continue with others
- Tracks active judge tasks in module-level dict (like `_active_runners`)

**2. Judge API endpoints** in `routers/benchmarks.py`
- `POST /benchmarks/{id}/judge` — trigger evaluation (returns immediately, background task)
- `GET /benchmarks/{id}/judge-status` — progress (total, completed, failed, pending)
- `GET /benchmarks/{id}/judge-scores` — aggregated scores (per-dimension averages, per-profile)

**3. Judge aggregation** in `quality_scorer.py`
- `aggregate_judge_scores(all_scores)` — same pattern as `aggregate_quality_scores`

---

#### Phase 10d: Judge Frontend

**1. "Run AI Judge" button** on BenchmarkRun Overview tab (completed benchmarks only)
- Only visible when judge endpoint is configured and enabled
- Shows judge status badge (not started / running / completed / partial / failed)
- Poll `GET /judge-status` while running

**2. JudgeScorecard component** — new `frontend/src/components/JudgeScorecard.jsx`
- Overall judge score, per-dimension bars (relevance, helpfulness, accuracy, depth)
- Displayed below heuristic QualityScorecard, visually distinct section
- Shows "X of Y requests judged" progress

**3. Judge comparison** in `BenchmarkCompare.jsx`
- If both benchmarks have judge scores, show judge dimension comparison

---

### Workstream 2: Concurrent Benchmark Warning

#### Phase 10e: Backend + Frontend (single phase)

**1. Backend check** in `routers/benchmarks.py` `start_benchmark()`
- After loading endpoint, query for running/pending benchmarks on same endpoint_id
- If found and `force` not set, return 409 with warning message + conflict details
- Add `force: bool = False` to `BenchmarkCreate` schema

**2. Frontend dialog** in `Benchmarks.jsx`
- Modify `handleStart` to handle 409 response
- Show confirmation dialog: warning text, list of conflicting runs, "Cancel" / "Run Anyway"
- "Run Anyway" re-sends with `force=true`
- Modify `client.js` to return warning object on 409 instead of throwing

**Not a hard block** — users may intentionally want concurrent benchmarks.

---

### Workstream 3: Live Dashboard Widgets

#### Phase 10f: Broadcast Live Quality Scores via WebSocket

**1. Running quality accumulators** in `collector.py` `MetricCollector`
- Add `_quality_scores_sum: dict[str, float]` and `_quality_scores_count: int`
- Accumulate in `record()` when `row.quality_scores` is computed
- Property `running_quality_scores` → returns running averages (or None if count=0)

**2. Extend WebSocket broadcast** in `snapshots.py` `_generate()`
- Add `quality_scores` and `quality_scored_count` to `snapshot_data` dict

---

#### Phase 10g: Live QualityScorecard Widget

**1. Refactor QualityScorecard** to accept live data
- Accept optional `liveScores` prop (from WebSocket snapshot)
- When provided, render from live data instead of API fetch
- Show "Live" badge with pulse dot, hide per-profile table and flag distribution in live mode
- Minimum threshold: show only after 10+ scored responses

**2. Wire into BenchmarkRun live view**
- Pass latest snapshot's `quality_scores` + `quality_scored_count` to QualityScorecard
- Show below the live metric cards during active runs

---

### Implementation Order

| # | Phase | Scope | Depends On |
|---|-------|-------|------------|
| 1 | **10e** — Concurrent warning | Backend + frontend | None |
| 2 | **10a** — Heuristic improvements | Backend + frontend | None |
| 3 | **10f** — WS quality broadcast | Backend | None |
| 4 | **10g** — Live QualityScorecard | Frontend | 10f |
| 5 | **10b** — Judge data model + settings | Backend + frontend | None |
| 6 | **10c** — Judge engine | Backend | 10b |
| 7 | **10d** — Judge frontend | Frontend | 10c |

Phases 1-4 are quick wins (small changes, no migrations). Phases 5-7 are the larger LLM-as-Judge feature.

### Verification per phase
1. `docker compose exec lm-lens-api pytest -v` — all tests pass
2. Manual test per the phase's test plan
3. User confirms before moving to next phase
4. Git commit per phase

---

## Key Files to Modify

| File | Phases |
|------|--------|
| `backend/app/engine/collector.py` | 10a, 10f |
| `backend/app/engine/quality_scorer.py` | 10a, 10c |
| `backend/app/engine/snapshots.py` | 10f |
| `backend/app/routers/benchmarks.py` | 10c, 10e |
| `backend/app/schemas/benchmark.py` | 10e |
| `frontend/src/components/QualityScorecard.jsx` | 10a, 10g |
| `frontend/src/pages/BenchmarkCompare.jsx` | 10a, 10d |
| `frontend/src/pages/BenchmarkRun.jsx` | 10d, 10g |
| `frontend/src/pages/Benchmarks.jsx` | 10e |
| `frontend/src/api/client.js` | 10d, 10e |
| **New files** | |
| `backend/app/models/settings.py` | 10b |
| `backend/app/routers/settings.py` | 10b |
| `backend/app/engine/judge.py` | 10c |
| `frontend/src/pages/Settings.jsx` | 10b |
| `frontend/src/components/JudgeScorecard.jsx` | 10d |

---

## Test Suite
129 tests passing (16 quality scorer + 3 quality API + 110 existing)

## User's Hardware Setup
- Development machine: Windows 11 Pro
- Inference machine: NVIDIA DGX Spark (Grace Blackwell GPU) at 192.168.178.189
- llama.cpp on port 8080 (Qwen3-Coder — very slow, 55s TTFT)
- vLLM on port 8000

## Endpoints configured in LM Lens:
- "DGX Spark - Gemma4" → http://192.168.178.189:8000
- "DGX Spark - Qwen3-Coder-Next - llama.cpp" → http://192.168.178.189:8080
- "Mock LLM" → http://lm-lens-mock:8000
