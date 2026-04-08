# Session Handoff — Ready for Phase 8

## Current State (2026-04-08)

All Phase 7 work is **committed** (phases 7a-7f). Uncommitted changes from this session need one final commit.

### Uncommitted changes:
- `PROGRESS.md` — updated with all 7f work
- `CLAUDE.md` — updated seeding docs, removed lens.bat references
- `frontend/src/pages/Benchmarks.jsx` — seed InfoTip, auto-generated 4-digit seed
- `frontend/src/pages/Profiles.jsx` — built-in profiles show Edit button
- `frontend/src/pages/ProfileEditor.jsx` — save in header, Reset to Defaults for built-in
- `frontend/src/pages/ScenarioEditor.jsx` — save button in header
- `frontend/src/api/client.js` — added profilesApi.reset()
- `backend/app/routers/profiles.py` — removed is_builtin 403 guard, added reset endpoint
- `backend/app/seed_data/runner.py` — only-if-missing seeding, reset_profile_to_defaults()
- `mock-llm/main.py` — respects max_tokens, returns finish_reason "length"
- `lens.bat` — deleted

### What was done this session:
1. **Bug fixes (committed as bdd4d47):**
   - Deterministic snapshot ordering for seeded benchmarks
   - Seeded multi-turn conversation history accumulation  
   - Request body mutation fix (stored snapshot, not live reference)
   - Comparison page: per-side prompts for non-seeded runs
   - maxTurns based on actual requests, not prompt plan

2. **Phase 7f polish (committed as 2b90768):**
   - Quality flag counts on Overview tab
   - Mock server finish_reason "length" support

3. **Additional polish (uncommitted):**
   - Seed input InfoTip tooltip
   - Save buttons in Profile/Scenario editor headers
   - Auto-generated 4-digit seeds (every run is reproducible)
   - Built-in profiles are editable with Reset to Defaults
   - Seed runner changed to only-if-missing (user edits survive restarts)
   - lens.bat removed, docker compose commands documented directly

---

## Next Up: Phase 8 — Load Curves & Breaking Point Detection

From PROGRESS.md:
- [ ] Load curve visualization in scenario builder
- [ ] Step / ramp / spike / wave curve implementations
- [ ] Breaking point auto-detection (latency spike, error threshold)
- [ ] Breaking point marker on dashboard timeline

### Context:
The scenario builder already has three test modes: Stress Test, Ramp Up, Breaking Point. The backend runner already implements stress and ramp modes. Breaking point mode exists but the auto-detection logic (latency spike, error threshold crossing) needs work. The frontend has no load curve visualization yet.

### Deferred Polish (Phase 9):
A visual polish audit was done this session. Key items identified:
- Reusable Spinner component (6+ bare text loading states)
- RequestLog empty state (currently returns null)
- Silent API error handling across components
- Chart empty states (LatencyTimeline, ThroughputChart)
- Response truncation UX (no expand option)
- Delete confirmation auto-dismiss
- Success feedback toasts

---

## Key Architecture Notes
- Backend engine code: `backend/app/engine/` (runner.py, conversation.py, llm_client.py, collector.py, prompt_plan.py)
- Load config stored in scenario: `scenario.load_config` (test_mode, duration_seconds, ramp params, breaking_criteria)
- Breaking criteria schema: `BreakingCriteria` in `backend/app/schemas/scenario.py`
- Runner modes: `_run_stress()`, `_run_ramp()`, `_run_breaking_point()` in `runner.py`
- Charts: `frontend/src/components/charts/` (LatencyTimeline, ThroughputChart, ErrorChart, ProfileBreakdown)
