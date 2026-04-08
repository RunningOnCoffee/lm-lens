from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.engine.collector import MetricCollector
from app.engine.conversation import ConversationSimulator, SessionConfig
from app.engine.llm_client import LLMClient
from app.engine.snapshots import SnapshotGenerator, percentile, ws_manager
from app.models.benchmark import Benchmark, BenchmarkRequest, BenchmarkSnapshot

logger = logging.getLogger(__name__)

# Module-level registry of active runners (for abort lookup)
_active_runners: dict[UUID, BenchmarkRunner] = {}


def get_active_runner(benchmark_id: UUID) -> BenchmarkRunner | None:
    return _active_runners.get(benchmark_id)


class BenchmarkRunner:
    """Orchestrates an entire benchmark run: virtual users, load patterns, metrics."""

    def __init__(
        self,
        benchmark_id: UUID,
        scenario_snapshot: dict,
        endpoint_snapshot: dict,
        session_factory,
        prompt_plan: list[dict] | None = None,
    ) -> None:
        self._benchmark_id = benchmark_id
        self._scenario = scenario_snapshot
        self._endpoint = endpoint_snapshot
        self._session_factory = session_factory
        self._prompt_plan = prompt_plan
        self._abort_event = asyncio.Event()
        self._user_aborted = False
        self._llm_client: LLMClient | None = None
        self._collector: MetricCollector | None = None
        self._snapshot_gen: SnapshotGenerator | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._active_user_count: int = 0

    async def run(self) -> None:
        _active_runners[self._benchmark_id] = self
        try:
            await self._update_status("running")
            self._setup()
            self._snapshot_gen.started_at = datetime.now(timezone.utc)
            await self._collector.start_flush_loop()
            await self._snapshot_gen.start()
            await self._execute_load_pattern()
            if self._user_aborted:
                await self._finalize("aborted")
            else:
                await self._finalize("completed")
        except Exception as e:
            logger.exception("Benchmark %s failed", self._benchmark_id)
            await self._finalize("failed", error=str(e))
        finally:
            await self._cleanup()
            _active_runners.pop(self._benchmark_id, None)

    def _setup(self) -> None:
        self._llm_client = LLMClient(
            endpoint_url=self._endpoint["endpoint_url"],
            api_key=self._endpoint.get("api_key"),
            model_name=self._endpoint["model_name"],
            llm_params=self._scenario.get("llm_params", {}),
            stream=True,
        )
        self._collector = MetricCollector(self._benchmark_id, self._session_factory)

        # Build profile ID → name mapping for readable per-profile keys
        profile_names: dict[str, str] = {}
        for sp in self._scenario.get("profiles", []):
            profile = sp.get("profile", {})
            pid = str(profile.get("id", ""))
            name = profile.get("name", pid[:8] if pid else "unknown")
            profile_names[pid] = name

        self._snapshot_gen = SnapshotGenerator(
            self._benchmark_id, self._collector, self._session_factory,
            profile_names=profile_names,
        )
        max_conc = self._scenario.get("max_concurrency", 100)
        self._semaphore = asyncio.Semaphore(max_conc)

        # Pass timing info to snapshot generator for broadcast
        load_config = self._scenario.get("load_config", {})
        self._snapshot_gen.duration_seconds = float(load_config.get("duration_seconds", 60))

    def _increment_active_users(self) -> None:
        self._active_user_count += 1
        self._snapshot_gen.active_users = self._active_user_count

    def _decrement_active_users(self) -> None:
        self._active_user_count -= 1
        self._snapshot_gen.active_users = self._active_user_count

    async def _execute_load_pattern(self) -> None:
        load_config = self._scenario.get("load_config", {})
        mode = load_config.get("test_mode", "stress")

        if mode == "stress":
            await self._run_stress(load_config)
        elif mode == "ramp":
            await self._run_ramp(load_config)
        elif mode == "breaking_point":
            await self._run_breaking_point(load_config)

    async def _run_stress(self, config: dict) -> None:
        """All users start simultaneously, loop sessions for duration_seconds."""
        duration = config.get("duration_seconds", 60)
        sessions = self._build_all_sessions()

        tasks = [
            asyncio.create_task(self._run_user(sc))
            for sc in sessions
        ]

        # Wait for duration or user abort
        try:
            await asyncio.wait_for(self._abort_event.wait(), timeout=duration)
        except asyncio.TimeoutError:
            pass  # Normal: duration elapsed

        self._abort_event.set()
        await self._cancel_tasks(tasks)

    async def _run_ramp(self, config: dict) -> None:
        """Add users in steps over time. Each user loops sessions until duration ends."""
        duration = config.get("duration_seconds", 60)
        step_size = config.get("ramp_users_per_step", 1)
        interval = config.get("ramp_interval_seconds", 10)
        sessions = self._build_all_sessions()
        tasks: list[asyncio.Task] = []
        idx = 0

        while idx < len(sessions) and not self._abort_event.is_set():
            batch = sessions[idx:idx + step_size]
            for sc in batch:
                tasks.append(asyncio.create_task(self._run_user(sc)))
            idx += step_size

            # Wait for interval or abort
            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=interval)
                break  # Abort was requested
            except asyncio.TimeoutError:
                pass

        # All users launched (or aborted). Wait for remaining duration.
        # Each user loops until abort_event is set, so we just wait for duration.
        elapsed_launching = idx / max(step_size, 1) * interval
        remaining = max(0, duration - elapsed_launching)
        if remaining > 0 and not self._abort_event.is_set():
            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                pass

        self._abort_event.set()
        await self._cancel_tasks(tasks)

    async def _run_breaking_point(self, config: dict) -> None:
        """Ramp until breaking criteria are breached for 3 consecutive snapshots."""
        duration = config.get("duration_seconds", 300)
        step_size = config.get("ramp_users_per_step", 1)
        interval = config.get("ramp_interval_seconds", 10)
        criteria = config.get("breaking_criteria", {})
        max_ttft = criteria.get("max_ttft_ms", 5000)
        max_itl = criteria.get("max_itl_ms", 500)
        max_error_rate = criteria.get("max_error_rate_pct", 10.0)
        consecutive_threshold = 3

        sessions = self._build_all_sessions()
        tasks: list[asyncio.Task] = []
        idx = 0
        breach_count = 0
        start = asyncio.get_event_loop().time()

        while idx < len(sessions) and not self._abort_event.is_set():
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= duration:
                break

            batch = sessions[idx:idx + step_size]
            for sc in batch:
                tasks.append(asyncio.create_task(self._run_user(sc)))
            idx += step_size

            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass

            # Check latest snapshot for breaking criteria
            if await self._check_breaking(max_ttft, max_itl, max_error_rate):
                breach_count += 1
                if breach_count >= consecutive_threshold:
                    logger.info("Breaking point reached after %d consecutive breaches", breach_count)
                    break
            else:
                breach_count = 0

        self._abort_event.set()
        await self._cancel_tasks(tasks)

    async def _check_breaking(
        self, max_ttft: float, max_itl: float, max_error_rate: float
    ) -> bool:
        """Check if the latest snapshot exceeds breaking criteria."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(BenchmarkSnapshot)
                    .where(BenchmarkSnapshot.benchmark_id == self._benchmark_id)
                    .order_by(BenchmarkSnapshot.timestamp.desc())
                    .limit(1)
                )
                snap = result.scalar_one_or_none()
                if not snap:
                    return False

                # Check TTFT
                if snap.p95_ttft_ms and snap.p95_ttft_ms > max_ttft:
                    return True

                # Check error rate
                total = snap.completed_requests + snap.failed_requests
                if total > 0:
                    error_rate = (snap.failed_requests / total) * 100
                    if error_rate > max_error_rate:
                        return True

                # Check ITL via per-request data (use throughput as proxy —
                # if TGT is way higher than TTFT, tokens are slow)
                if snap.p95_tgt_ms and snap.p50_ttft_ms:
                    avg_itl_approx = (snap.p95_tgt_ms - snap.p50_ttft_ms) / max(1, snap.throughput_tps / max(1, snap.throughput_rps))
                    if avg_itl_approx > max_itl:
                        return True

                return False
        except Exception:
            logger.exception("Error checking breaking criteria")
            return False

    async def _run_user(self, session_config: SessionConfig) -> None:
        """Run a single virtual user, looping sessions until abort event is set."""
        self._increment_active_users()
        try:
            while not self._abort_event.is_set():
                async with self._semaphore:
                    self._snapshot_gen.requests_in_flight += 1
                    try:
                        sim = ConversationSimulator(
                            config=session_config,
                            llm_client=self._llm_client,
                            collector=self._collector,
                            abort_event=self._abort_event,
                        )
                        await sim.run()
                    finally:
                        self._snapshot_gen.requests_in_flight -= 1
        finally:
            self._decrement_active_users()

    def _build_all_sessions(self) -> list[SessionConfig]:
        """Build SessionConfig for each virtual user from the scenario snapshot."""
        # If we have a prompt plan (seeded mode), build sessions from it
        if self._prompt_plan:
            return self._build_seeded_sessions()

        sessions: list[SessionConfig] = []
        profiles_data = self._scenario.get("profiles", [])

        for sp in profiles_data:
            profile = sp.get("profile", {})
            behavior = sp.get("behavior_overrides") or profile.get("behavior_defaults", {})
            user_count = sp.get("user_count", 1)

            # Resolve templates
            templates = []
            for t in profile.get("conversation_templates", []):
                templates.append({
                    "starter_prompt": t.get("starter_prompt", "Hello"),
                    "follow_ups": t.get("follow_ups", []),
                })

            # Resolve universal follow-ups
            universal_fus = [
                fp.get("content", "")
                for fp in profile.get("follow_up_prompts", [])
                if fp.get("is_universal", False)
            ]

            # Resolve variables
            variables = {
                v["name"]: v.get("values", [])
                for v in profile.get("template_variables", [])
            }

            turns = behavior.get("turns_per_session", {"min": 1, "max": 3})
            think = behavior.get("think_time_seconds", {"min": 1, "max": 5})
            sess = behavior.get("sessions_per_user", {"min": 1, "max": 1})

            config = SessionConfig(
                profile_id=uuid.UUID(profile["id"]) if isinstance(profile.get("id"), str) else profile.get("id", uuid.uuid4()),
                session_mode=behavior.get("session_mode", "multi_turn"),
                turns_per_session=(turns.get("min", 1), turns.get("max", 3)),
                think_time_seconds=(think.get("min", 1.0), think.get("max", 5.0)),
                sessions_per_user=(sess.get("min", 1), sess.get("max", 1)),
                read_time_factor=behavior.get("read_time_factor", 0.02),
                templates=templates,
                universal_follow_ups=universal_fus,
                variables=variables,
            )

            for _ in range(user_count):
                sessions.append(config)

        return sessions

    def _build_seeded_sessions(self) -> list[SessionConfig]:
        """Build SessionConfigs from a pre-generated prompt plan."""
        # Build a behavior lookup by profile_id
        behavior_map: dict[str, dict] = {}
        for sp in self._scenario.get("profiles", []):
            profile = sp.get("profile", {})
            pid = str(profile.get("id", ""))
            behavior = sp.get("behavior_overrides") or profile.get("behavior_defaults", {})
            behavior_map[pid] = behavior

        sessions: list[SessionConfig] = []
        for entry in self._prompt_plan:
            pid = entry["profile_id"]
            behavior = behavior_map.get(pid, {})
            think = behavior.get("think_time_seconds", {"min": 1, "max": 5})

            config = SessionConfig(
                profile_id=uuid.UUID(pid),
                session_mode="multi_turn",
                turns_per_session=(len(entry["prompts"]), len(entry["prompts"])),
                think_time_seconds=(think.get("min", 1.0), think.get("max", 5.0)),
                sessions_per_user=(1, 1),
                read_time_factor=behavior.get("read_time_factor", 0.02),
                seeded_prompts=entry["prompts"],
                session_index=entry["session_index"],
            )
            sessions.append(config)

        return sessions

    def abort(self) -> None:
        self._user_aborted = True
        self._abort_event.set()

    @staticmethod
    async def _cancel_tasks(tasks: list[asyncio.Task], grace_seconds: float = 3.0) -> None:
        """Wait briefly for tasks to finish, then cancel any still running."""
        if not tasks:
            return
        done, pending = await asyncio.wait(tasks, timeout=grace_seconds)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _update_status(self, status: str, error: str | None = None) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Benchmark).where(Benchmark.id == self._benchmark_id)
            )
            benchmark = result.scalar_one()
            benchmark.status = status
            if status == "running":
                benchmark.started_at = datetime.now(timezone.utc)
            if status in ("completed", "failed", "aborted"):
                benchmark.completed_at = datetime.now(timezone.utc)
            if error:
                benchmark.error_message = error
            await session.commit()

    async def _finalize(self, status: str, error: str | None = None) -> None:
        if self._snapshot_gen:
            await self._snapshot_gen.stop()
        if self._collector:
            await self._collector.stop()

        # Compute results summary
        summary = await self._compute_summary()

        async with self._session_factory() as session:
            result = await session.execute(
                select(Benchmark).where(Benchmark.id == self._benchmark_id)
            )
            benchmark = result.scalar_one()
            benchmark.status = status
            benchmark.completed_at = datetime.now(timezone.utc)
            benchmark.results_summary = summary
            if error:
                benchmark.error_message = error
            await session.commit()

        # Clean up WebSocket connections
        ws_manager.cleanup(self._benchmark_id)

    async def _compute_summary(self) -> dict:
        """Compute percentile-based results from benchmark_requests."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(
                        BenchmarkRequest.turn_number,
                        BenchmarkRequest.ttft_ms,
                        BenchmarkRequest.tgt_ms,
                        BenchmarkRequest.tokens_per_second,
                        BenchmarkRequest.input_tokens,
                        BenchmarkRequest.output_tokens,
                        BenchmarkRequest.error_type,
                        BenchmarkRequest.quality_flags,
                        BenchmarkRequest.created_at,
                    ).where(
                        BenchmarkRequest.benchmark_id == self._benchmark_id
                    )
                )
                rows = result.all()

                if not rows:
                    return {"total_requests": 0, "error": "No requests recorded"}

                total = len(rows)
                errors = sum(1 for r in rows if r.error_type is not None)
                ok_rows = [r for r in rows if r.error_type is None]

                # TTFT split by turn number
                ttft_t1 = [r.ttft_ms for r in ok_rows if r.ttft_ms is not None and r.turn_number == 0]
                ttft_multi = [r.ttft_ms for r in ok_rows if r.ttft_ms is not None and r.turn_number > 0]
                ttft_all = [r.ttft_ms for r in ok_rows if r.ttft_ms is not None]

                # Generation speed
                tps_all = [r.tokens_per_second for r in ok_rows if r.tokens_per_second is not None]

                # Total generation time
                tgt_all = [r.tgt_ms for r in ok_rows if r.tgt_ms is not None]

                # Token totals
                total_input = sum(r.input_tokens or 0 for r in rows)
                total_output = sum(r.output_tokens or 0 for r in rows)

                # Throughput: successful requests per second over actual run duration
                timestamps = [r.created_at for r in rows if r.created_at is not None]
                duration = 0.0
                if len(timestamps) >= 2:
                    duration = (max(timestamps) - min(timestamps)).total_seconds()

                # Quality flag counts
                qf_counts: dict[str, int] = {}
                for r in rows:
                    if r.quality_flags:
                        for flag in r.quality_flags:
                            qf_counts[flag] = qf_counts.get(flag, 0) + 1

                return {
                    "total_requests": total,
                    "successful_requests": total - errors,
                    "failed_requests": errors,
                    "error_rate_pct": round(errors / total * 100, 2) if total > 0 else 0,
                    "quality_flags": qf_counts,
                    # First-turn TTFT (primary LLM comparison metric)
                    "ttft_t1_p50_ms": _round(percentile(ttft_t1, 50)),
                    "ttft_t1_p95_ms": _round(percentile(ttft_t1, 95)),
                    # All-turns TTFT
                    "ttft_all_p50_ms": _round(percentile(ttft_all, 50)),
                    "ttft_all_p95_ms": _round(percentile(ttft_all, 95)),
                    # Multi-turn TTFT (context-heavy, null if single-turn only)
                    "ttft_multi_p50_ms": _round(percentile(ttft_multi, 50)),
                    "ttft_multi_p95_ms": _round(percentile(ttft_multi, 95)),
                    # Generation speed
                    "tps_p50": _round(percentile(tps_all, 50)),
                    "tps_p5": _round(percentile(tps_all, 5)),
                    # Total generation time
                    "tgt_p50_ms": _round(percentile(tgt_all, 50)),
                    "tgt_p95_ms": _round(percentile(tgt_all, 95)),
                    # Totals
                    "total_input_tokens": total_input,
                    "total_output_tokens": total_output,
                    "avg_throughput_rps": round((total - errors) / duration, 2) if duration > 0 else 0,
                }
        except Exception:
            logger.exception("Error computing summary")
            return {"error": "Failed to compute summary"}


    async def _cleanup(self) -> None:
        if self._llm_client:
            await self._llm_client.close()


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None
