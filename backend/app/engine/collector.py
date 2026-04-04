from __future__ import annotations

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from app.engine.llm_client import LLMRequestResult
from app.models.benchmark import BenchmarkRequest

logger = logging.getLogger(__name__)


class MetricCollector:
    """Collects per-request metrics, buffers them, and flushes to Postgres in batches."""

    def __init__(self, benchmark_id: UUID, session_factory) -> None:
        self._benchmark_id = benchmark_id
        self._session_factory = session_factory
        self._buffer: list[BenchmarkRequest] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_batch_size = 100
        self._flush_interval = 1.0

        # In-memory window for snapshot generator (drained every 1s)
        self._window: list[LLMRequestResult] = []
        self._window_profiles: list[UUID | None] = []
        self._window_turns: list[int] = []
        self._window_lock = asyncio.Lock()
        self._total_completed = 0
        self._total_failed = 0

        # Rolling 30-second window for live metric cards
        # Each deque entry is one second's batch of (result, turn_number) tuples
        self._rolling_deque: deque[list[tuple[LLMRequestResult, int]]] = deque(maxlen=30)
        self._rolling_staging: list[tuple[LLMRequestResult, int]] = []

        self._flush_task: asyncio.Task | None = None

    async def record(
        self,
        result: LLMRequestResult,
        profile_id: UUID | None,
        session_id: UUID,
        turn_number: int,
    ) -> None:
        """Record a single request result."""
        row = BenchmarkRequest(
            id=uuid.uuid4(),
            benchmark_id=self._benchmark_id,
            profile_id=profile_id,
            session_id=session_id,
            turn_number=turn_number,
            ttft_ms=result.ttft_ms,
            tgt_ms=result.tgt_ms,
            inter_token_latencies=result.inter_token_latencies or None,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            tokens_per_second=result.tokens_per_second,
            http_status=result.http_status,
            error_type=result.error_type,
            error_detail=result.error_detail,
            model_reported=result.model_reported,
            request_body=result.request_body,
            response_text=result.response_text or None,
            created_at=datetime.now(timezone.utc),
        )

        async with self._buffer_lock:
            self._buffer.append(row)
            should_flush = len(self._buffer) >= self._flush_batch_size

        async with self._window_lock:
            self._window.append(result)
            self._window_profiles.append(profile_id)
            self._window_turns.append(turn_number)
            self._rolling_staging.append((result, turn_number))
            if result.success:
                self._total_completed += 1
            else:
                self._total_failed += 1

        if should_flush:
            await self.flush()

    async def start_flush_loop(self) -> None:
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
        except asyncio.CancelledError:
            pass

    async def flush(self) -> None:
        async with self._buffer_lock:
            if not self._buffer:
                return
            batch = self._buffer
            self._buffer = []

        try:
            async with self._session_factory() as session:
                session.add_all(batch)
                await session.commit()
        except Exception:
            logger.exception("Failed to flush %d metric records", len(batch))

    async def take_window(self) -> tuple[list[LLMRequestResult], list[UUID | None], list[int]]:
        """Atomically swap the in-memory window and return results + profile IDs + turn numbers."""
        async with self._window_lock:
            results = self._window
            profiles = self._window_profiles
            turns = self._window_turns
            self._window = []
            self._window_profiles = []
            self._window_turns = []
            # Push this second's results into the rolling deque
            if self._rolling_staging:
                self._rolling_deque.append(self._rolling_staging)
                self._rolling_staging = []
            else:
                # Still push an empty batch so the deque advances each second
                self._rolling_deque.append([])
            return results, profiles, turns

    @property
    def total_completed(self) -> int:
        return self._total_completed

    @property
    def total_failed(self) -> int:
        return self._total_failed

    @property
    def rolling_results(self) -> list[tuple[LLMRequestResult, int]]:
        """Flattened list of (result, turn_number) from the last ~30 seconds."""
        return [item for batch in self._rolling_deque for item in batch]

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
