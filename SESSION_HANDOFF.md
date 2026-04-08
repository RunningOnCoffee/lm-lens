# Session Handoff — Phase 8 In Progress

## Current State (2026-04-08)

Phase 8 is **mostly complete** — only 8e remains. Everything below needs one commit.

### Phase 8 completed sub-phases:

**8a: Load Curve Engine (Backend)**
- New `backend/app/engine/load_curves.py` — 4 curve types: Step, Linear, Spike, Wave
- Each has `target_users(elapsed, total_users, duration) -> int`
- `create_curve(load_config) -> LoadCurve` factory
- `LoadConfig` schema extended: `load_curve`, `spike_at_pct`, `spike_duration_seconds`, `wave_period_seconds`
- Runner refactored: `_run_ramp` and `_run_breaking_point` delegate to `_run_with_curve()`
- New `_run_curve_user()` — voluntarily exits when curve reduces target count
- `_check_breaking()` now returns reason string (ttft/error_rate/itl) instead of bool
- Breaking point details saved to `results_summary.breaking_point`
- 24 tests for curves in `tests/test_load_curves.py`

**8b: Load Curve Preview (Frontend)**
- New `frontend/src/components/LoadCurvePreview.jsx` — Recharts AreaChart mirroring backend formulas
- ScenarioEditor: 4-button curve selector (step/linear/spike/wave) for ramp/breaking_point modes
- Conditional parameter inputs per curve type
- Live preview chart updates reactively

**8c: Enhanced Quality Flags (Backend)**
- 4 new quality flag detectors in `collector.py`:
  - `invalid_json` — prompt asks for JSON, response isn't valid JSON
  - `format_noncompliant` — prompt asks for bullet list/code block/table, response lacks markers
  - `length_noncompliant` — prompt specifies sentence/word count, response deviates >3x or <0.3x
  - `wrong_language` — Unicode script mismatch between prompt and response
- Helper functions: `_extract_prompt_text`, `_check_json_validity`, `_check_format_compliance`, `_check_length_compliance`, `_check_language_match`
- `QualityFlagPill.jsx` updated with 4 new flag colors/labels
- "Quality Flag Tester" custom profile created via API (prompts designed to test all flags)
- 13 new tests in `test_engine.py`
- Note: flags are prompt-driven (analyze the prompt text for format requests). They only fire when profiles contain explicit format instructions AND the LLM fails to follow them.

**8d: Breaking Point Marker + Quality in Snapshots**
- `BenchmarkSnapshot` model: added `quality_flag_count` column
- Migration `008_snapshot_quality.py`
- `MetricCollector`: tracks `_window_quality_flag_count` and `_total_quality_flagged`
- `take_window()` now returns 4 values: results, profiles, turns, qf_count
- `SnapshotGenerator`: passes quality flag count to snapshot, broadcasts via WebSocket
- `BenchmarkSnapshotRead` schema: includes `quality_flag_count`
- `LatencyTimeline.jsx`: accepts `breakingPoint` prop, renders red dashed ReferenceLine with label
- `BenchmarkRun.jsx`: passes `summary.breaking_point` to LatencyTimeline
- Quality flags are observational only — removed from breaking criteria (user decision: flags are for post-run analysis, not failure criteria)

### What still needs doing:

**8e: Quality-Under-Load Correlation Chart**
- New `frontend/src/components/charts/QualityLoadChart.jsx`
- X-axis: time (or active_users), Y-axis: quality flag rate %
- Data source: snapshots have `quality_flag_count`, `completed_requests`, `active_users`
- Integrate into BenchmarkRun page (Overview tab, below existing charts)
- Only show if any quality flags exist

### Also fixed this session:
- `test_update_builtin_profile_fails` renamed to `test_update_builtin_profile_allowed` (Phase 7f made built-in profiles editable)
- `test_collector_record_and_window` updated for 4-value `take_window()` return

---

## Key Files Modified This Session

### Backend
- `backend/app/engine/load_curves.py` — NEW: load curve implementations
- `backend/app/engine/runner.py` — refactored ramp/breaking_point, _run_with_curve, _run_curve_user
- `backend/app/engine/collector.py` — 4 new quality detectors, quality flag count tracking
- `backend/app/engine/snapshots.py` — quality_flag_count in snapshots + broadcast
- `backend/app/schemas/scenario.py` — LoadConfig extended with curve fields
- `backend/app/schemas/benchmark.py` — BenchmarkSnapshotRead + quality_flag_count
- `backend/app/models/benchmark.py` — BenchmarkSnapshot + quality_flag_count column
- `backend/alembic/versions/008_snapshot_quality.py` — NEW: migration
- `backend/tests/test_load_curves.py` — NEW: 24 tests
- `backend/tests/test_engine.py` — 13 new quality flag tests, fixed 2 existing tests
- `backend/tests/test_profiles.py` — fixed stale test

### Frontend
- `frontend/src/components/LoadCurvePreview.jsx` — NEW: curve preview chart
- `frontend/src/components/QualityFlagPill.jsx` — 4 new flag styles/labels
- `frontend/src/components/charts/LatencyTimeline.jsx` — breaking point ReferenceLine
- `frontend/src/pages/ScenarioEditor.jsx` — curve selector, preview, cleaned up breaking criteria
- `frontend/src/pages/BenchmarkRun.jsx` — passes breakingPoint prop

### Other
- `PROGRESS.md` — updated Phase 8 items, reorganized Phase 9/10

---

## Architecture Notes for 8e

The quality-under-load chart needs:
- **Live mode**: snapshots from WebSocket contain `quality_flag_count` per second and `active_users`
- **Historical mode**: GET /benchmarks/{id}/snapshots returns `quality_flag_count` per snapshot
- Compute rate: `quality_flag_count / (completed_requests_delta)` per snapshot interval
- Consider cumulative rate: `quality_flag_total / completed_requests` for smoother curve
- The `quality_flag_total` field is broadcast via WebSocket but NOT stored in DB (it's a running counter on the collector)
- For historical, you can derive cumulative from summing snapshot `quality_flag_count` values

## Test Suite
110 tests passing (24 load curves + 13 new quality flags + 73 existing)
