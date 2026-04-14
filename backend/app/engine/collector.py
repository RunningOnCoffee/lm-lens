from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
import uuid
from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from app.engine.llm_client import LLMRequestResult
from app.engine.quality_scorer import compute_quality_scores
from app.models.benchmark import BenchmarkRequest

logger = logging.getLogger(__name__)

# Refusal detection patterns — only checked against first 300 chars of response
_REFUSAL_PATTERNS = re.compile(
    r"(?i)\b("
    r"I cannot|I can't|I'm not able to|I am not able to|"
    r"I'm unable to|I am unable to|"
    r"I must decline|I have to decline|"
    r"I'm sorry, but I'm not able|my guidelines prevent|it would be inappropriate|"
    r"as an AI|as a language model|as an artificial intelligence"
    r")\b"
)

# Phrases that look like refusals but aren't
_REFUSAL_FALSE_POSITIVES = re.compile(
    r"(?i)("
    r"I cannot stress|I cannot overstate|I can't help but|I cannot emphasize|"
    r"I can't overstate|I can't stress|I cannot help but"
    r")"
)


# JSON request detection — only trigger when the prompt explicitly asks for JSON output
_JSON_REQUEST_PATTERNS = re.compile(
    r"(?i)("
    r"respond\s+(in|with|using)\s+json|"
    r"return\s+(a\s+)?json|"
    r"output\s+(as\s+|in\s+)?json|"
    r"format\s+(as\s+|in\s+|your\s+(response|answer|output)\s+(as\s+|in\s+))?json|"
    r"give\s+me\s+(a\s+)?json|"
    r"provide\s+(a\s+)?json|"
    r"in\s+json\s+format|"
    r"as\s+a\s+json\s+(object|array|response)"
    r")"
)

# Format request patterns and their expected markers in the response
_FORMAT_CHECKS = [
    # (pattern to find in prompt, markers to find in response, flag description)
    (re.compile(r"(?i)(bullet|bulleted)\s+(list|point)"), [r"^\s*[-*•]\s", r"^\s*\d+[\.\)]\s"]),
    (re.compile(r"(?i)numbered\s+list"), [r"^\s*\d+[\.\)]\s"]),
    (re.compile(r"(?i)markdown\s+table"), [r"\|.*\|"]),
    (re.compile(r"(?i)(code\s+block|```|fenced\s+code)"), [r"```"]),
]

# Length request patterns — captures the number and unit
_LENGTH_PATTERNS = [
    (re.compile(r"(?i)in\s+(\d+)\s+sentences?"), "sentences"),
    (re.compile(r"(?i)in\s+(\d+)\s+words?"), "words"),
    (re.compile(r"(?i)in\s+(\d+)\s+paragraphs?"), "paragraphs"),
    (re.compile(r"(?i)(\d+)\s+sentences?\s+(or\s+less|max|maximum)"), "sentences"),
    (re.compile(r"(?i)(\d+)\s+words?\s+(or\s+less|max|maximum)"), "words"),
]


def _extract_prompt_text(result: LLMRequestResult) -> str:
    """Extract the user's prompt text from the request body for quality analysis."""
    body = result.request_body
    if not body:
        return ""
    messages = body.get("messages", [])
    # Concatenate all user messages (the prompt the LLM was given)
    parts = []
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
    return " ".join(parts)


def _check_json_validity(prompt: str, response: str) -> bool:
    """Flag if the prompt explicitly asks for JSON and the response is not valid JSON."""
    if not _JSON_REQUEST_PATTERNS.search(prompt):
        return False
    # Try to extract JSON from the response (may be wrapped in markdown code block)
    text = response.strip()
    if text.startswith("```"):
        # Strip markdown code fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        json.loads(text)
        return False  # Valid JSON
    except (json.JSONDecodeError, ValueError):
        return True  # Invalid JSON


def _check_format_compliance(prompt: str, response: str) -> bool:
    """Flag if the prompt asks for a specific format and the response lacks it."""
    for pattern, markers in _FORMAT_CHECKS:
        if pattern.search(prompt):
            # Check if any expected marker is present in the response
            found = any(
                re.search(marker, response, re.MULTILINE)
                for marker in markers
            )
            if not found:
                return True  # Format requested but not found
    return False


def _check_length_compliance(prompt: str, response: str) -> bool:
    """Flag if the prompt specifies a length and the response deviates significantly."""
    for pattern, unit in _LENGTH_PATTERNS:
        match = pattern.search(prompt)
        if not match:
            continue
        requested = int(match.group(1))
        if requested <= 0:
            continue

        if unit == "sentences":
            # Count sentences by splitting on period/exclamation/question + space or end
            actual = len(re.findall(r"[.!?]+(?:\s|$)", response))
            actual = max(actual, 1) if response.strip() else 0
        elif unit == "words":
            actual = len(response.split())
        elif unit == "paragraphs":
            actual = len([p for p in response.split("\n\n") if p.strip()])
        else:
            continue

        # Flag if more than 3x or less than 0.3x the requested amount
        if requested > 0 and (actual > requested * 3 or actual < requested * 0.3):
            return True
    return False


def _check_language_match(prompt: str, response: str) -> bool:
    """Flag if the response language script doesn't match the prompt language script.

    Uses Unicode script detection — conservative, only flags clear mismatches
    like a Latin prompt getting a CJK response.
    """
    if len(prompt) < 20 or len(response) < 20:
        return False  # Too short to judge

    def dominant_script(text: str) -> str | None:
        """Return the dominant Unicode script category of alphabetic chars."""
        counts: dict[str, int] = {}
        for ch in text:
            if not ch.isalpha():
                continue
            cat = unicodedata.category(ch)
            # Use the Unicode block as a rough script indicator
            cp = ord(ch)
            if cp < 0x0080:
                script = "latin"
            elif 0x0400 <= cp <= 0x04FF:
                script = "cyrillic"
            elif 0x0600 <= cp <= 0x06FF:
                script = "arabic"
            elif 0x3040 <= cp <= 0x30FF or 0x4E00 <= cp <= 0x9FFF:
                script = "cjk"
            elif 0xAC00 <= cp <= 0xD7AF:
                script = "korean"
            elif 0x0900 <= cp <= 0x097F:
                script = "devanagari"
            else:
                script = "other"
            counts[script] = counts.get(script, 0) + 1
        if not counts:
            return None
        total = sum(counts.values())
        top_script = max(counts, key=counts.get)
        # Only return if one script is clearly dominant (>60%)
        if counts[top_script] / total > 0.6:
            return top_script
        return None

    prompt_script = dominant_script(prompt)
    response_script = dominant_script(response)

    if not prompt_script or not response_script:
        return False
    # Only flag if both have a clear dominant script and they differ
    return prompt_script != response_script


def _check_text_repetition(response: str) -> bool:
    """Detect repeated text via N-gram analysis.

    Flags if any single 5-gram appears in >30% of positions,
    or if the same sentence appears 3+ times.
    Skips responses under 100 chars.
    """
    if len(response) < 100:
        return False

    # Sentence-level check: same sentence 3+ times
    sentences = [s.strip() for s in re.split(r"[.!?]+", response) if len(s.strip()) > 10]
    if sentences:
        from collections import Counter
        sentence_counts = Counter(sentences)
        if sentence_counts and sentence_counts.most_common(1)[0][1] >= 3:
            return True

    # 5-gram check
    words = response.lower().split()
    if len(words) < 10:
        return False
    ngrams: dict[tuple, int] = {}
    n = 5
    total_positions = len(words) - n + 1
    if total_positions <= 0:
        return False
    for i in range(total_positions):
        gram = tuple(words[i:i + n])
        ngrams[gram] = ngrams.get(gram, 0) + 1
    max_count = max(ngrams.values())
    if max_count / total_positions > 0.3:
        return True

    return False



def _compute_quality_flags(result: LLMRequestResult) -> list[str] | None:
    """Compute quality flags for a completed request."""
    flags: list[str] = []

    # Empty response
    if not result.response_text or (result.output_tokens is not None and result.output_tokens == 0):
        flags.append("empty")
        return flags  # No point checking other flags on empty

    # Truncated (hit max_tokens)
    if result.finish_reason == "length":
        flags.append("truncated")

    # Refusal detection — only check first 300 chars (refusals are always up front)
    if result.response_text:
        head = result.response_text[:300]
        if _REFUSAL_PATTERNS.search(head) and not _REFUSAL_FALSE_POSITIVES.search(head):
            flags.append("refusal")

    # Repeated tokens — ITL-based check OR text N-gram analysis
    itl_flagged = False
    itls = result.inter_token_latencies
    if itls and len(itls) >= 20:
        mean = sum(itls) / len(itls)
        if mean > 0:
            variance = sum((x - mean) ** 2 for x in itls) / len(itls)
            cv = (variance ** 0.5) / mean  # coefficient of variation
            # Very low CV with many tokens suggests degenerate repetition
            if cv < 0.1 and result.output_tokens and result.output_tokens > 50:
                itl_flagged = True

    if itl_flagged or _check_text_repetition(result.response_text or ""):
        flags.append("repeated_tokens")

    # --- New quality checks (Phase 8c) ---
    prompt = _extract_prompt_text(result)
    response = result.response_text or ""

    if prompt and response:
        if _check_json_validity(prompt, response):
            flags.append("invalid_json")

        if _check_format_compliance(prompt, response):
            flags.append("format_noncompliant")

        if _check_length_compliance(prompt, response):
            flags.append("length_noncompliant")

        if _check_language_match(prompt, response):
            flags.append("wrong_language")

    return flags if flags else None


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
        self._window_quality_flag_count: int = 0
        self._window_lock = asyncio.Lock()
        self._total_completed = 0
        self._total_failed = 0
        self._total_quality_flagged = 0

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
            quality_flags=(
                _compute_quality_flags(result)
                if result.success and result.finish_reason != "aborted"
                else None
            ),
            quality_scores=None,  # set below after flags are known
            created_at=datetime.now(timezone.utc),
        )

        # Compute quality dimension scores from flags (skip aborted requests)
        if result.finish_reason != "aborted" and (
            row.quality_flags is not None or (result.success and row.quality_flags is None)
        ):
            # Successful, non-aborted request: score it (None flags means empty list = perfect)
            flags = row.quality_flags if row.quality_flags else []
            row.quality_scores = compute_quality_scores(flags)

        has_quality_flags = bool(row.quality_flags)

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
            if has_quality_flags:
                self._window_quality_flag_count += 1
                self._total_quality_flagged += 1

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

    async def take_window(self) -> tuple[list[LLMRequestResult], list[UUID | None], list[int], int]:
        """Atomically swap the in-memory window and return results + profile IDs + turn numbers + quality flag count."""
        async with self._window_lock:
            results = self._window
            profiles = self._window_profiles
            turns = self._window_turns
            qf_count = self._window_quality_flag_count
            self._window = []
            self._window_profiles = []
            self._window_turns = []
            self._window_quality_flag_count = 0
            # Push this second's results into the rolling deque
            if self._rolling_staging:
                self._rolling_deque.append(self._rolling_staging)
                self._rolling_staging = []
            else:
                # Still push an empty batch so the deque advances each second
                self._rolling_deque.append([])
            return results, profiles, turns, qf_count

    @property
    def total_completed(self) -> int:
        return self._total_completed

    @property
    def total_failed(self) -> int:
        return self._total_failed

    @property
    def total_quality_flagged(self) -> int:
        return self._total_quality_flagged

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
