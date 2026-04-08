# Session Handoff — Phase 7 Bug Fixes

## Current State (2026-04-07)

Phases 7a-7b are **committed**. Phases 7c-7e have **uncommitted code** that mostly works but has two critical bugs in the seeded benchmark feature.

### Uncommitted files:
- `PROGRESS.md`
- `backend/alembic/versions/007_benchmark_seed.py` (new)
- `backend/app/engine/prompt_plan.py` (new)
- `backend/app/engine/conversation.py`
- `backend/app/engine/runner.py`
- `backend/app/models/benchmark.py`
- `backend/app/routers/benchmarks.py`
- `backend/app/schemas/benchmark.py`
- `frontend/src/App.jsx`
- `frontend/src/api/client.js`
- `frontend/src/pages/BenchmarkCompare.jsx` (new)
- `frontend/src/pages/BenchmarkRun.jsx`
- `frontend/src/pages/Benchmarks.jsx`
- `frontend/src/stores/benchmarkStore.js`
- `frontend/src/components/QualityFlagPill.jsx` (new)
- `frontend/src/components/ResponseBrowser.jsx` (new)

### What was built in 7c-7e:
- **7c: Response Browser** — Session-grouped conversation view with chat-style bubbles, markdown rendering (react-markdown + remark-gfm), ITL sparklines, profile filter, pagination
- **7d: Export** — CSV/JSON download buttons on BenchmarkRun header
- **7e: Comparison Mode** — "Compare Runs" button on Benchmarks list, guided selection UX, BenchmarkCompare page with Metrics tab (side-by-side stats, delta badges, profile comparison table) and Responses tab (side-by-side session browser)
- **7e also added: Seeded Benchmarks** — seed input on Benchmarks page, `prompt_plan.py` generates deterministic prompt plans, stored as JSONB, used by runner

---

## Bug 1: Seeded Prompt Plan Not Deterministic

**Symptom:** Two benchmarks with same scenario + seed=42 produce DIFFERENT prompts and different turn counts.

**Root Cause:** `_build_scenario_snapshot()` in `benchmarks.py:80-130` iterates SQLAlchemy relationships loaded via `selectinload`. None of these relationships have `order_by` defined:

- `Scenario.profiles` (`models/scenario.py:47`)
- `Profile.conversation_templates` (`models/profile.py:29`)
- `ConversationTemplate.follow_ups` (`models/profile.py:57`)
- `Profile.follow_up_prompts` (`models/profile.py:32`)
- `Profile.template_variables` (`models/profile.py:35`)

SQLAlchemy `selectinload` does NOT guarantee ordering. If templates come back as `[T1, T2]` in run A but `[T2, T1]` in run B, then `rng.choice(templates)` with the same seed picks a different template. This cascades through the entire prompt plan.

**Fix:**
1. Sort all lists in `_build_scenario_snapshot()` by stable keys (e.g., `str(profile.id)`, `str(t.id)`, `v.name`) before serializing to the snapshot dict
2. Add `order_by` to the relationship definitions in the models as defense-in-depth

**Files to modify:**
- `backend/app/routers/benchmarks.py` — sort in `_build_scenario_snapshot()`
- `backend/app/models/profile.py` — add `order_by` to 4 relationships
- `backend/app/models/scenario.py` — add `order_by` to `Scenario.profiles`

---

## Bug 2: Seeded Multi-Turn Has No Conversation History

**Symptom:** In seeded mode, each turn is sent standalone — the LLM never sees prior messages, making follow-ups like "Can you elaborate?" meaningless.

**Current code** in `conversation.py:107-129`:
```python
async def _run_seeded(self) -> None:
    prompts = self._config.seeded_prompts
    for turn, prompt in enumerate(prompts):
        messages = [{"role": "user", "content": prompt}]  # <-- No history!
        result = await self._client.send(messages)
```

**Fix:** Accumulate messages list like the non-seeded `run()` method does:
```python
async def _run_seeded(self) -> None:
    prompts = self._config.seeded_prompts
    messages: list[dict] = []
    for turn, prompt in enumerate(prompts):
        messages.append({"role": "user", "content": prompt})
        result = await self._client.send(messages)
        # ... record ...
        if result.success and result.response_text:
            messages.append({"role": "assistant", "content": result.response_text})
```

User prompts stay deterministic (pre-generated). LLM responses will differ between endpoints (expected — that's what we're comparing).

**File to modify:** `backend/app/engine/conversation.py`

---

## Testing Plan (Run BEFORE Committing)

### Test 1: Prompt Plan Determinism
1. `lens up` to rebuild
2. Run benchmark A: pick any scenario, any endpoint, seed=42
3. Wait for completion
4. Run benchmark B: same scenario, same endpoint, seed=42
5. Compare prompt_plan in DB: `SELECT prompt_plan FROM benchmarks WHERE seed=42 ORDER BY created_at`
6. **Expected:** Identical prompt_plan JSONB in both rows

### Test 2: Multi-Turn Conversation History
1. Run seeded benchmark with multi-turn profile (Casual User, 2-3 turns)
2. Open Response Browser, expand a multi-turn session
3. **Expected:** Follow-up responses are contextually relevant (not confused by lack of context)

### Test 3: Comparison Page
1. Go to Benchmarks list, click "Compare Runs", select two seed=42 runs
2. **Expected:** Page loads, Metrics tab shows side-by-side stats with deltas
3. Switch to Responses tab
4. **Expected:** Matching user prompts, different LLM responses side by side

### Test 4: Export
1. On a completed benchmark, click Export CSV and Export JSON
2. **Expected:** Files download correctly

### Test 5: Response Browser (Single Run)
1. Open completed benchmark, go to Responses tab
2. Expand a session
3. **Expected:** Chat-style view with markdown-rendered responses

---

## Implementation Order
1. Fix `_build_scenario_snapshot()` sorting (Bug 1) — 4 files
2. Fix `_run_seeded()` conversation history (Bug 2) — 1 file
3. `lens up` to rebuild
4. Run Tests 1-5 with user confirmation
5. Fix any issues found
6. Commit 7c-7e
7. Proceed to 7f (polish: quality flag counts on Overview tab, finish_reason verification)

---

## Existing Plan File
There is also a plan at `C:\Users\Maddab\.claude\plans\radiant-dreaming-gosling.md` with the same information in a slightly different format.
