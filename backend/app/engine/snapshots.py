from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket

from app.engine.collector import MetricCollector
from app.engine.llm_client import LLMRequestResult
from app.models.benchmark import BenchmarkSnapshot

logger = logging.getLogger(__name__)


def percentile(values: list[float], p: float) -> float | None:
    """Compute interpolated percentile (0-100) from a sorted list."""
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


class WebSocketManager:
    """Manages WebSocket connections per benchmark for live metric streaming."""

    def __init__(self) -> None:
        self._connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, benchmark_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(benchmark_id, []).append(ws)

    async def disconnect(self, benchmark_id: UUID, ws: WebSocket) -> None:
        conns = self._connections.get(benchmark_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(benchmark_id, None)

    async def broadcast(self, benchmark_id: UUID, data: dict) -> None:
        conns = self._connections.get(benchmark_id, [])
        if not conns:
            return
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)

    def cleanup(self, benchmark_id: UUID) -> None:
        self._connections.pop(benchmark_id, None)


# Module-level singleton
ws_manager = WebSocketManager()


class SnapshotGenerator:
    """Generates 1-second aggregated metric snapshots and broadcasts via WebSocket."""

    def __init__(
        self,
        benchmark_id: UUID,
        collector: MetricCollector,
        session_factory,
        profile_names: dict[str, str] | None = None,
    ) -> None:
        self._benchmark_id = benchmark_id
        self._collector = collector
        self._session_factory = session_factory
        self._profile_names = profile_names or {}
        self._task: asyncio.Task | None = None
        self.active_users: int = 0
        self.requests_in_flight: int = 0
        self.started_at: datetime | None = None
        self.duration_seconds: float = 0

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(1.0)
                await self._generate()
        except asyncio.CancelledError:
            pass

    async def _generate(self) -> None:
        results, profile_ids = await self._collector.take_window()

        snapshot = self._compute(results, profile_ids)

        # Write to DB
        try:
            async with self._session_factory() as session:
                session.add(snapshot)
                await session.commit()
        except Exception:
            logger.exception("Failed to write snapshot")

        # Compute rolling-window metrics (last ~30 seconds)
        rolling = self._collector.rolling_results
        rolling_ttft_all = [r.ttft_ms for r, _ in rolling if r.success and r.ttft_ms is not None]
        rolling_ttft_t1 = [r.ttft_ms for r, t in rolling if r.success and r.ttft_ms is not None and t == 0]
        rolling_tps = [r.tokens_per_second for r, _ in rolling if r.success and r.tokens_per_second is not None]

        # Elapsed time
        elapsed = 0.0
        if self.started_at:
            elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()

        # Broadcast via WebSocket
        snapshot_data = {
            "timestamp": snapshot.timestamp.isoformat(),
            "active_users": snapshot.active_users,
            "requests_in_flight": snapshot.requests_in_flight,
            "completed_requests": snapshot.completed_requests,
            "failed_requests": snapshot.failed_requests,
            # Per-window percentiles (for timeline charts)
            "p50_ttft_ms": snapshot.p50_ttft_ms,
            "p95_ttft_ms": snapshot.p95_ttft_ms,
            "p99_ttft_ms": snapshot.p99_ttft_ms,
            "p50_tgt_ms": snapshot.p50_tgt_ms,
            "p95_tgt_ms": snapshot.p95_tgt_ms,
            "p99_tgt_ms": snapshot.p99_tgt_ms,
            "throughput_rps": snapshot.throughput_rps,
            "throughput_tps": snapshot.throughput_tps,
            "error_count": snapshot.error_count,
            "per_profile": snapshot.per_profile,
            # Rolling 30s percentiles — all turns
            "rolling_p50_ttft_ms": percentile(rolling_ttft_all, 50),
            "rolling_p95_ttft_ms": percentile(rolling_ttft_all, 95),
            # Rolling 30s percentiles — first turn only (pure LLM responsiveness)
            "rolling_p50_ttft_t1_ms": percentile(rolling_ttft_t1, 50),
            "rolling_p95_ttft_t1_ms": percentile(rolling_ttft_t1, 95),
            # Rolling 30s generation speed
            "rolling_avg_tps": sum(rolling_tps) / len(rolling_tps) if rolling_tps else None,
            "rolling_p5_tps": percentile(rolling_tps, 5),
            # Timing
            "elapsed_seconds": elapsed,
            "duration_seconds": self.duration_seconds,
        }
        await ws_manager.broadcast(self._benchmark_id, snapshot_data)

    def _compute(
        self,
        results: list[LLMRequestResult],
        profile_ids: list[UUID | None],
    ) -> BenchmarkSnapshot:
        now = datetime.now(timezone.utc)

        ttft_values = [r.ttft_ms for r in results if r.ttft_ms is not None]
        tgt_values = [r.tgt_ms for r in results if r.tgt_ms is not None]
        ok_count = sum(1 for r in results if r.success)
        err_count = sum(1 for r in results if not r.success)
        total_output_tokens = sum(r.output_tokens or 0 for r in results)

        # Per-profile breakdown (use readable names)
        per_profile: dict[str, dict] = {}
        for result, pid in zip(results, profile_ids):
            pid_str = str(pid) if pid else "unknown"
            key = self._profile_names.get(pid_str, pid_str[:8])
            if key not in per_profile:
                per_profile[key] = {
                    "completed": 0, "failed": 0,
                    "ttft_values": [], "tps_values": [],
                    "output_tokens": 0,
                }
            entry = per_profile[key]
            if result.success:
                entry["completed"] += 1
            else:
                entry["failed"] += 1
            if result.ttft_ms is not None:
                entry["ttft_values"].append(result.ttft_ms)
            if result.tokens_per_second is not None:
                entry["tps_values"].append(result.tokens_per_second)
            entry["output_tokens"] += result.output_tokens or 0

        # Compute per-profile percentiles and clean up raw values
        for entry in per_profile.values():
            entry["p50_ttft_ms"] = percentile(entry.pop("ttft_values"), 50)
            tps_vals = entry.pop("tps_values")
            entry["avg_tps"] = sum(tps_vals) / len(tps_vals) if tps_vals else None

        return BenchmarkSnapshot(
            id=uuid.uuid4(),
            benchmark_id=self._benchmark_id,
            timestamp=now,
            active_users=self.active_users,
            requests_in_flight=self.requests_in_flight,
            completed_requests=self._collector.total_completed,
            failed_requests=self._collector.total_failed,
            p50_ttft_ms=percentile(ttft_values, 50),
            p95_ttft_ms=percentile(ttft_values, 95),
            p99_ttft_ms=percentile(ttft_values, 99),
            p50_tgt_ms=percentile(tgt_values, 50),
            p95_tgt_ms=percentile(tgt_values, 95),
            p99_tgt_ms=percentile(tgt_values, 99),
            throughput_rps=float(ok_count),  # requests in this 1-second window
            throughput_tps=float(total_output_tokens),  # tokens in this 1-second window
            error_count=err_count,
            per_profile=per_profile if per_profile else None,
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Generate one final snapshot
        await self._generate()
