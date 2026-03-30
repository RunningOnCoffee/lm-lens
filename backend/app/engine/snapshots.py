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
    ) -> None:
        self._benchmark_id = benchmark_id
        self._collector = collector
        self._session_factory = session_factory
        self._task: asyncio.Task | None = None
        self.active_users: int = 0
        self.requests_in_flight: int = 0

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

        # Broadcast via WebSocket
        snapshot_data = {
            "timestamp": snapshot.timestamp.isoformat(),
            "active_users": snapshot.active_users,
            "requests_in_flight": snapshot.requests_in_flight,
            "completed_requests": snapshot.completed_requests,
            "failed_requests": snapshot.failed_requests,
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

        # Per-profile breakdown
        per_profile: dict[str, dict] = {}
        for result, pid in zip(results, profile_ids):
            key = str(pid) if pid else "unknown"
            if key not in per_profile:
                per_profile[key] = {
                    "completed": 0, "failed": 0,
                    "ttft_values": [], "tgt_values": [],
                    "output_tokens": 0,
                }
            entry = per_profile[key]
            if result.success:
                entry["completed"] += 1
            else:
                entry["failed"] += 1
            if result.ttft_ms is not None:
                entry["ttft_values"].append(result.ttft_ms)
            if result.tgt_ms is not None:
                entry["tgt_values"].append(result.tgt_ms)
            entry["output_tokens"] += result.output_tokens or 0

        # Compute per-profile percentiles and clean up raw values
        for entry in per_profile.values():
            entry["p50_ttft_ms"] = percentile(entry.pop("ttft_values"), 50)
            entry["p50_tgt_ms"] = percentile(entry.pop("tgt_values"), 50)

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
