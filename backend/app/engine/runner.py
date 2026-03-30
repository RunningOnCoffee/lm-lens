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
from app.engine.snapshots import SnapshotGenerator, ws_manager
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
        session_factory,
    ) -> None:
        self._benchmark_id = benchmark_id
        self._scenario = scenario_snapshot
        self._session_factory = session_factory
        self._abort_event = asyncio.Event()
        self._user_aborted = False
        self._llm_client: LLMClient | None = None
        self._collector: MetricCollector | None = None
        self._snapshot_gen: SnapshotGenerator | None = None
        self._semaphore: asyncio.Semaphore | None = None

    async def run(self) -> None:
        _active_runners[self._benchmark_id] = self
        try:
            await self._update_status("running")
            self._setup()
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
            endpoint_url=self._scenario["endpoint_url"],
            api_key=self._scenario.get("api_key"),
            model_name=self._scenario["model_name"],
            llm_params=self._scenario.get("llm_params", {}),
            stream=True,
        )
        self._collector = MetricCollector(self._benchmark_id, self._session_factory)
        self._snapshot_gen = SnapshotGenerator(
            self._benchmark_id, self._collector, self._session_factory
        )
        max_conc = self._scenario.get("max_concurrency", 100)
        self._semaphore = asyncio.Semaphore(max_conc)

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
        """All users start simultaneously, run for duration_seconds."""
        duration = config.get("duration_seconds", 60)
        sessions = self._build_all_sessions()
        self._snapshot_gen.active_users = len(sessions)

        tasks = [
            asyncio.create_task(self._run_user(sc, duration))
            for sc in sessions
        ]

        # Wait for duration or abort
        try:
            await asyncio.wait_for(self._abort_event.wait(), timeout=duration)
        except asyncio.TimeoutError:
            pass  # Normal: duration elapsed

        self._abort_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_ramp(self, config: dict) -> None:
        """Add users in steps over time."""
        duration = config.get("duration_seconds", 60)
        step_size = config.get("ramp_users_per_step", 1)
        interval = config.get("ramp_interval_seconds", 10)
        sessions = self._build_all_sessions()
        tasks: list[asyncio.Task] = []
        idx = 0
        start = asyncio.get_event_loop().time()

        while idx < len(sessions) and not self._abort_event.is_set():
            elapsed = asyncio.get_event_loop().time() - start
            remaining = duration - elapsed
            if remaining <= 0:
                break

            batch = sessions[idx:idx + step_size]
            for sc in batch:
                tasks.append(asyncio.create_task(self._run_user(sc, remaining)))
            idx += step_size
            self._snapshot_gen.active_users = min(idx, len(sessions))

            # Wait for interval or abort
            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=min(interval, remaining))
                break
            except asyncio.TimeoutError:
                pass

        # Wait for remaining duration
        elapsed = asyncio.get_event_loop().time() - start
        remaining = max(0, duration - elapsed)
        if remaining > 0 and not self._abort_event.is_set():
            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                pass

        self._abort_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)

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
            remaining = duration - elapsed
            if remaining <= 0:
                break

            batch = sessions[idx:idx + step_size]
            for sc in batch:
                tasks.append(asyncio.create_task(self._run_user(sc, remaining)))
            idx += step_size
            self._snapshot_gen.active_users = min(idx, len(sessions))

            try:
                await asyncio.wait_for(self._abort_event.wait(), timeout=min(interval, remaining))
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
        await asyncio.gather(*tasks, return_exceptions=True)

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

    async def _run_user(self, session_config: SessionConfig, max_duration: float) -> None:
        """Run a single virtual user for up to max_duration seconds."""
        start = asyncio.get_event_loop().time()
        min_s, max_s = session_config.sessions_per_user
        num_sessions = random.randint(min_s, max_s)

        for _ in range(num_sessions):
            if self._abort_event.is_set():
                return
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= max_duration:
                return

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

    def _build_all_sessions(self) -> list[SessionConfig]:
        """Build SessionConfig for each virtual user from the scenario snapshot."""
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

    def abort(self) -> None:
        self._user_aborted = True
        self._abort_event.set()

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
        """Compute aggregate results from benchmark_requests."""
        try:
            async with self._session_factory() as session:
                base = select(BenchmarkRequest).where(
                    BenchmarkRequest.benchmark_id == self._benchmark_id
                )

                # Total counts
                count_result = await session.execute(
                    select(func.count(BenchmarkRequest.id)).where(
                        BenchmarkRequest.benchmark_id == self._benchmark_id
                    )
                )
                total = count_result.scalar() or 0

                error_count_result = await session.execute(
                    select(func.count(BenchmarkRequest.id)).where(
                        BenchmarkRequest.benchmark_id == self._benchmark_id,
                        BenchmarkRequest.error_type.isnot(None),
                    )
                )
                errors = error_count_result.scalar() or 0

                # Aggregates
                agg_result = await session.execute(
                    select(
                        func.avg(BenchmarkRequest.ttft_ms),
                        func.avg(BenchmarkRequest.tgt_ms),
                        func.avg(BenchmarkRequest.tokens_per_second),
                        func.sum(BenchmarkRequest.input_tokens),
                        func.sum(BenchmarkRequest.output_tokens),
                    ).where(
                        BenchmarkRequest.benchmark_id == self._benchmark_id
                    )
                )
                row = agg_result.one()

                return {
                    "total_requests": total,
                    "successful_requests": total - errors,
                    "failed_requests": errors,
                    "error_rate_pct": round((errors / total * 100), 2) if total > 0 else 0,
                    "avg_ttft_ms": round(row[0], 2) if row[0] else None,
                    "avg_tgt_ms": round(row[1], 2) if row[1] else None,
                    "avg_tps": round(row[2], 2) if row[2] else None,
                    "total_input_tokens": row[3] or 0,
                    "total_output_tokens": row[4] or 0,
                }
        except Exception:
            logger.exception("Error computing summary")
            return {"error": "Failed to compute summary"}

    async def _cleanup(self) -> None:
        if self._llm_client:
            await self._llm_client.close()
