# Session Handoff — Phase 9 Complete + Bug Fix

## Current State (2026-04-13)

Phase 9 (A/B Quality Comparison) is **complete and committed**. Profile refinement is **complete**. Seeded prompt variety bug is **fixed**. 129 tests passing.

### What was done this session:

**Phase 9a: Quality Scoring Engine**
- New `backend/app/engine/quality_scorer.py` — computes per-request dimension scores from quality flags
- 4 dimensions: completeness (30%), compliance (30%), coherence (20%), safety (20%)
- Flag-to-penalty mapping: empty→completeness -1.0, truncated→-0.5, invalid_json→compliance -1.0, etc.
- Per-request scores stored in new `quality_scores` JSONB column (migration `009_quality_scores.py`)
- Scoring integrated into `collector.py` at write time

**Phase 9b: Quality Scores API + Aggregation**
- `GET /benchmarks/{id}/quality-scores` — returns overall scores, per-profile breakdown, flag distribution
- `aggregate_quality_scores()` averages dimension scores across requests
- Enhanced `/compare` endpoint with quality_comparison (per-dimension a/b/delta, overall winner)

**Phase 9c: Quality Scorecard UI**
- New `frontend/src/components/QualityScorecard.jsx` — overall score, dimension bars, flag distribution, per-profile table
- Integrated into BenchmarkRun Overview tab

**Phase 9d: Quality Comparison UI**
- QualityWinnerBanner, QualityDimensionComparison, QualityFlagDiff components in BenchmarkCompare.jsx
- Side-by-side bars (cyan=A, amber=B), delta values, flag count comparison

**Aborted Requests Excluded from Scoring**
- Requests with `finish_reason="aborted"` skip quality flag computation and quality scoring entirely
- They get `quality_flags=None` and `quality_scores=None`, excluded from all aggregation

**Built-in Profile Refinement**
- Reduced from 11 profiles to 4: Casual User, Power User/Researcher, Programmer, Data Analyst
- Programmer: fixed `$CODE_BLOCK` variable, added 6 real code snippets (86-97 lines each)
- Casual User: added opinion and trivia templates, expanded variables
- Power User: added strategic-assessment template, more follow-ups
- Data Analyst: added metrics-design and statistical-analysis templates

**Bug Fix: Seeded Prompt Variety**
- Seeded benchmarks were sending the same prompt every loop iteration in stress mode
- Root cause: `_build_seeded_sessions()` didn't populate templates/variables, and `seeded_prompts` was never cleared after first use
- Fix: seeded SessionConfigs now carry full template/variable data; `seeded_prompts` cleared after first session so subsequent loops use random selection
- Applies to both `_run_user` (stress) and `_run_curve_user` (ramp/breaking point)

**Test Cleanup**
- Tests no longer leave data in the DB — ID-tracking approach in `conftest.py`

### TODO for next session:
- Phase 10: Polish & Documentation
- Quality scoring is heuristic-only — LLM-as-Judge is in the roadmap for real quality evaluation

---

## Key Files Changed

| File | What |
|------|------|
| `backend/app/engine/quality_scorer.py` | NEW — scoring engine |
| `backend/app/engine/collector.py` | Quality scoring at write time, abort exclusion |
| `backend/app/engine/runner.py` | Seeded session bug fix, quality aggregation in summary |
| `backend/app/models/benchmark.py` | `quality_scores` JSONB column |
| `backend/app/schemas/benchmark.py` | `quality_scores` in response schema |
| `backend/app/routers/benchmarks.py` | `/quality-scores` endpoint, enhanced `/compare` |
| `backend/app/seed_data/profiles.py` | 4 refined profiles with real code snippets |
| `backend/alembic/versions/009_quality_scores.py` | Migration |
| `backend/tests/conftest.py` | ID-tracking cleanup |
| `backend/tests/test_benchmarks.py` | Quality score tests + track_created |
| `backend/tests/test_quality_scorer.py` | 16 scorer unit tests |
| `frontend/src/components/QualityScorecard.jsx` | NEW — scorecard widget |
| `frontend/src/pages/BenchmarkRun.jsx` | Scorecard integration |
| `frontend/src/pages/BenchmarkCompare.jsx` | Quality comparison UI |
| `frontend/src/api/client.js` | `qualityScores()` API call |

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
