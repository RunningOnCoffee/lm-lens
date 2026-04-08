"""Tests for the benchmark engine components."""

import asyncio
import json
import time
import uuid

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.engine.llm_client import LLMClient, LLMRequestResult, _normalize_url
from app.engine.collector import MetricCollector, _compute_quality_flags
from app.engine.conversation import ConversationSimulator, SessionConfig
from app.engine.snapshots import SnapshotGenerator, WebSocketManager, percentile

# ---------------------------------------------------------------------------
# In-process mock LLM (tiny ASGI app for test isolation)
# ---------------------------------------------------------------------------

mock_llm = FastAPI()


@mock_llm.post("/v1/chat/completions")
async def mock_completions(request: dict):  # noqa: ARG001
    stream = request.get("stream", False)
    model = request.get("model", "test-model")
    prompt_tokens = 10
    completion_tokens = 5
    response_text = "Hello from the mock"

    if stream:
        async def generate():
            words = response_text.split()
            for i, word in enumerate(words):
                chunk = {
                    "id": "test-id",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": word if i == 0 else f" {word}"},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.01)
            # Final chunk with usage
            final = {
                "id": "test-id",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return {
        "id": "test-id",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


mock_llm_error = FastAPI()


@mock_llm_error.post("/v1/chat/completions")
async def mock_error(request: dict):  # noqa: ARG001
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "Internal server error"}},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(app, *, stream: bool = True) -> LLMClient:
    """Create an LLMClient with an in-process test transport."""
    transport = httpx.ASGITransport(app=app)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return LLMClient(
        endpoint_url="http://test",
        api_key=None,
        model_name="test-model",
        llm_params={"temperature": 0.7},
        stream=stream,
        http_client=http_client,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_normalize_url_bare():
    assert _normalize_url("http://localhost:8080") == "http://localhost:8080/v1/chat/completions"


def test_normalize_url_with_v1():
    assert _normalize_url("http://localhost:8080/v1") == "http://localhost:8080/v1/chat/completions"


def test_normalize_url_already_full():
    assert _normalize_url("http://localhost:8080/v1/chat/completions") == "http://localhost:8080/v1/chat/completions"


def test_normalize_url_trailing_slash():
    assert _normalize_url("http://localhost:8080/") == "http://localhost:8080/v1/chat/completions"


async def test_llm_client_non_streaming():
    client = _make_client(mock_llm, stream=False)
    try:
        result = await client.send([{"role": "user", "content": "Hello"}])
        assert result.success is True
        assert result.http_status == 200
        assert result.ttft_ms is not None
        assert result.tgt_ms is not None
        assert result.ttft_ms == result.tgt_ms  # non-streaming: TTFT = TGT
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.tokens_per_second is not None
        assert result.tokens_per_second > 0
        assert result.response_text == "Hello from the mock"
        assert result.model_reported == "test-model"
        assert result.request_body is not None
        assert result.request_body["model"] == "test-model"
    finally:
        await client.close()


async def test_llm_client_streaming():
    client = _make_client(mock_llm, stream=True)
    try:
        result = await client.send([{"role": "user", "content": "Hello"}])
        assert result.success is True
        assert result.http_status == 200
        assert result.ttft_ms is not None
        assert result.tgt_ms is not None
        assert result.ttft_ms <= result.tgt_ms
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.response_text == "Hello from the mock"
        assert result.model_reported == "test-model"
        # Streaming should have inter-token latencies (4 words = 3 gaps)
        assert len(result.inter_token_latencies) == 3
        assert all(itl > 0 for itl in result.inter_token_latencies)
    finally:
        await client.close()


async def test_llm_client_http_error():
    client = _make_client(mock_llm_error, stream=False)
    try:
        result = await client.send([{"role": "user", "content": "Hello"}])
        assert result.success is False
        assert result.http_status == 500
        assert result.error_type == "http_5xx"
        assert result.error_detail is not None
    finally:
        await client.close()


async def test_llm_client_streaming_error():
    client = _make_client(mock_llm_error, stream=True)
    try:
        result = await client.send([{"role": "user", "content": "Hello"}])
        assert result.success is False
        assert result.http_status == 500
        assert result.error_type == "http_5xx"
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Percentile tests
# ---------------------------------------------------------------------------

def test_percentile_empty():
    assert percentile([], 50) is None


def test_percentile_single():
    assert percentile([42.0], 50) == 42.0
    assert percentile([42.0], 99) == 42.0


def test_percentile_multiple():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 50) == 30.0
    p95 = percentile(values, 95)
    assert p95 is not None
    assert 46.0 <= p95 <= 50.0


def test_percentile_unsorted():
    """Input doesn't need to be pre-sorted."""
    values = [50.0, 10.0, 30.0, 40.0, 20.0]
    assert percentile(values, 50) == 30.0


# ---------------------------------------------------------------------------
# MetricCollector tests
# ---------------------------------------------------------------------------

def _make_result(*, success: bool = True, ttft_ms: float = 100.0, tgt_ms: float = 500.0,
                 output_tokens: int = 50) -> LLMRequestResult:
    return LLMRequestResult(
        success=success,
        ttft_ms=ttft_ms,
        tgt_ms=tgt_ms,
        input_tokens=10,
        output_tokens=output_tokens,
        tokens_per_second=output_tokens / (tgt_ms / 1000) if tgt_ms else None,
        http_status=200 if success else 500,
        error_type=None if success else "http_5xx",
        response_text="test response",
    )


async def test_collector_record_and_window():
    """record() adds to window; take_window() drains it."""
    benchmark_id = uuid.uuid4()
    # We don't need a real DB session factory for this test — flush won't be called
    collector = MetricCollector(benchmark_id, session_factory=None)

    profile_id = uuid.uuid4()
    session_id = uuid.uuid4()

    await collector.record(_make_result(success=True), profile_id, session_id, 0)
    await collector.record(_make_result(success=False), profile_id, session_id, 1)

    assert collector.total_completed == 1
    assert collector.total_failed == 1

    results, profiles, turns, qf_count = await collector.take_window()
    assert len(results) == 2
    assert len(profiles) == 2
    assert len(turns) == 2
    assert profiles[0] == profile_id

    # Window should be empty after take
    results2, profiles2, turns2, qf_count2 = await collector.take_window()
    assert len(results2) == 0
    assert len(profiles2) == 0


# ---------------------------------------------------------------------------
# SnapshotGenerator._compute() test
# ---------------------------------------------------------------------------

async def test_snapshot_compute():
    """_compute() correctly aggregates results into a snapshot."""
    benchmark_id = uuid.uuid4()
    collector = MetricCollector(benchmark_id, session_factory=None)

    profile_a = uuid.uuid4()
    profile_b = uuid.uuid4()

    results = [
        _make_result(success=True, ttft_ms=100.0, tgt_ms=500.0, output_tokens=50),
        _make_result(success=True, ttft_ms=200.0, tgt_ms=800.0, output_tokens=80),
        _make_result(success=False, ttft_ms=300.0, tgt_ms=1000.0, output_tokens=0),
    ]
    profile_ids = [profile_a, profile_a, profile_b]

    gen = SnapshotGenerator(benchmark_id, collector, session_factory=None)
    gen.active_users = 5
    gen.requests_in_flight = 2

    snapshot = gen._compute(results, profile_ids)

    assert snapshot.active_users == 5
    assert snapshot.requests_in_flight == 2
    assert snapshot.p50_ttft_ms == 200.0
    assert snapshot.throughput_rps == 2.0  # 2 successful
    assert snapshot.throughput_tps == 130.0  # 50 + 80 + 0
    assert snapshot.error_count == 1
    assert snapshot.per_profile is not None
    # Snapshot generator uses short profile IDs (first 8 chars) when no profile_names mapping
    key_a = str(profile_a)[:8]
    key_b = str(profile_b)[:8]
    assert key_a in snapshot.per_profile
    assert snapshot.per_profile[key_a]["completed"] == 2
    assert snapshot.per_profile[key_b]["failed"] == 1


# ---------------------------------------------------------------------------
# WebSocketManager test
# ---------------------------------------------------------------------------

async def test_ws_manager_broadcast():
    """WebSocketManager.broadcast() sends to connected clients."""
    manager = WebSocketManager()
    benchmark_id = uuid.uuid4()

    # Create a fake WebSocket that records sent data
    class FakeWS:
        def __init__(self):
            self.received = []
            self.accepted = False

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            self.received.append(data)

    ws = FakeWS()
    await manager.connect(benchmark_id, ws)
    assert ws.accepted is True

    await manager.broadcast(benchmark_id, {"test": "data"})
    assert len(ws.received) == 1
    assert ws.received[0] == {"test": "data"}

    await manager.disconnect(benchmark_id, ws)
    await manager.broadcast(benchmark_id, {"test": "data2"})
    # No more messages after disconnect
    assert len(ws.received) == 1


# ---------------------------------------------------------------------------
# ConversationSimulator tests
# ---------------------------------------------------------------------------

class FakeLLMClient:
    """Fake LLM client that returns canned results."""

    def __init__(self, responses: list[str] | None = None):
        self.calls: list[list[dict]] = []
        self._responses = responses or ["Fake response from the mock LLM"]
        self._idx = 0

    async def send(self, messages: list[dict]) -> LLMRequestResult:
        self.calls.append(list(messages))
        text = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return LLMRequestResult(
            success=True,
            ttft_ms=50.0,
            tgt_ms=200.0,
            input_tokens=10,
            output_tokens=len(text.split()),
            tokens_per_second=25.0,
            http_status=200,
            response_text=text,
        )

    async def close(self):
        pass


class FakeCollector:
    """Fake collector that just records calls."""

    def __init__(self):
        self.records: list[tuple] = []

    async def record(self, result, profile_id, session_id, turn_number):
        self.records.append((result, profile_id, session_id, turn_number))


def _make_session_config(**overrides) -> SessionConfig:
    defaults = dict(
        profile_id=uuid.uuid4(),
        session_mode="multi_turn",
        turns_per_session=(2, 2),  # exactly 2 turns
        think_time_seconds=(0.0, 0.0),  # no delay in tests
        sessions_per_user=(1, 1),
        read_time_factor=0.0,
        templates=[{
            "starter_prompt": "Hello $TOPIC, tell me about $SUBJECT",
            "follow_ups": [{"content": "Tell me more about $SUBJECT"}],
        }],
        universal_follow_ups=["Go on"],
        variables={"TOPIC": ["world"], "SUBJECT": ["testing", "code"]},
    )
    defaults.update(overrides)
    return SessionConfig(**defaults)


async def test_conversation_variable_substitution():
    """Variables in prompts are substituted."""
    config = _make_session_config(
        turns_per_session=(1, 1),
        variables={"TOPIC": ["world"], "SUBJECT": ["testing"]},
    )
    fake_llm = FakeLLMClient()
    fake_collector = FakeCollector()
    abort = asyncio.Event()

    sim = ConversationSimulator(config, fake_llm, fake_collector, abort)
    await sim.run()

    assert len(fake_llm.calls) == 1
    sent_prompt = fake_llm.calls[0][0]["content"]
    assert "$TOPIC" not in sent_prompt
    assert "$SUBJECT" not in sent_prompt
    assert "world" in sent_prompt
    assert "testing" in sent_prompt


async def test_conversation_multi_turn():
    """Multi-turn conversation sends correct number of messages."""
    config = _make_session_config(turns_per_session=(3, 3))
    fake_llm = FakeLLMClient()
    fake_collector = FakeCollector()
    abort = asyncio.Event()

    sim = ConversationSimulator(config, fake_llm, fake_collector, abort)
    await sim.run()

    # 3 turns = 3 LLM calls
    assert len(fake_llm.calls) == 3
    assert len(fake_collector.records) == 3

    # Conversation history grows: turn 0 has 1 user msg, turn 1 has 3 (user+asst+user), etc.
    assert len(fake_llm.calls[0]) == 1
    assert len(fake_llm.calls[1]) == 3  # user, assistant, user
    assert len(fake_llm.calls[2]) == 5  # user, assistant, user, assistant, user

    # All records share the same session_id
    session_ids = {r[2] for r in fake_collector.records}
    assert len(session_ids) == 1


async def test_conversation_abort():
    """Abort event stops the conversation mid-session."""
    config = _make_session_config(
        turns_per_session=(10, 10),
        think_time_seconds=(0.5, 0.5),  # enough delay for abort to fire
    )
    fake_llm = FakeLLMClient()
    fake_collector = FakeCollector()
    abort = asyncio.Event()

    sim = ConversationSimulator(config, fake_llm, fake_collector, abort)

    # Set abort after first turn completes (the interruptible sleep will catch it)
    async def set_abort():
        await asyncio.sleep(0.05)
        abort.set()

    asyncio.create_task(set_abort())
    await sim.run()

    # Should have completed fewer than 10 turns (abort fires during think time)
    assert len(fake_llm.calls) < 10


async def test_conversation_single_shot():
    """Single-shot mode only sends one turn."""
    config = _make_session_config(
        session_mode="single_shot",
        turns_per_session=(5, 5),  # should be ignored
    )
    fake_llm = FakeLLMClient()
    fake_collector = FakeCollector()
    abort = asyncio.Event()

    sim = ConversationSimulator(config, fake_llm, fake_collector, abort)
    await sim.run()

    assert len(fake_llm.calls) == 1


async def test_conversation_follow_up_priority():
    """Template-specific follow-ups are used over universal ones."""
    config = _make_session_config(
        turns_per_session=(2, 2),
        templates=[{
            "starter_prompt": "Start",
            "follow_ups": [{"content": "Template follow-up"}],
        }],
        universal_follow_ups=["Universal follow-up"],
    )
    fake_llm = FakeLLMClient()
    fake_collector = FakeCollector()
    abort = asyncio.Event()

    sim = ConversationSimulator(config, fake_llm, fake_collector, abort)
    await sim.run()

    # Second call's last message should be the template follow-up
    second_call_prompt = fake_llm.calls[1][-1]["content"]
    assert second_call_prompt == "Template follow-up"


# ---------------------------------------------------------------------------
# Quality Flag Detection Tests
# ---------------------------------------------------------------------------

def test_quality_flag_empty_response():
    """Empty response text triggers 'empty' flag."""
    result = LLMRequestResult(success=True, response_text="", output_tokens=0)
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "empty" in flags


def test_quality_flag_none_response():
    """None response text triggers 'empty' flag."""
    result = LLMRequestResult(success=True, response_text=None, output_tokens=5)
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "empty" in flags


def test_quality_flag_truncated():
    """finish_reason='length' triggers 'truncated' flag."""
    result = LLMRequestResult(
        success=True,
        response_text="Some truncated output...",
        output_tokens=100,
        finish_reason="length",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "truncated" in flags


def test_quality_flag_refusal():
    """Refusal patterns in response trigger 'refusal' flag."""
    result = LLMRequestResult(
        success=True,
        response_text="I cannot provide that information as an AI language model.",
        output_tokens=10,
        finish_reason="stop",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "refusal" in flags


def test_quality_flag_no_flags():
    """Normal response has no quality flags."""
    result = LLMRequestResult(
        success=True,
        response_text="Here is a perfectly normal helpful response about Python programming.",
        output_tokens=10,
        finish_reason="stop",
        inter_token_latencies=[10.0, 15.0, 8.0, 12.0, 20.0],
    )
    flags = _compute_quality_flags(result)
    assert flags is None


def test_quality_flag_repeated_tokens():
    """Very uniform ITL with many tokens triggers 'repeated_tokens' flag."""
    # 60 tokens with nearly identical inter-token latencies
    itls = [10.0] * 60
    result = LLMRequestResult(
        success=True,
        response_text="word " * 60,
        output_tokens=60,
        finish_reason="stop",
        inter_token_latencies=itls,
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "repeated_tokens" in flags


def test_quality_flag_finish_reason_captured():
    """LLMRequestResult correctly stores finish_reason."""
    result = LLMRequestResult(finish_reason="length")
    assert result.finish_reason == "length"


# --- Phase 8c: New quality flag detectors ---

def _make_quality_result(prompt: str, response: str, **kwargs) -> LLMRequestResult:
    """Helper to build a result with a user prompt in the request body."""
    return LLMRequestResult(
        success=True,
        response_text=response,
        output_tokens=len(response.split()),
        finish_reason="stop",
        request_body={"messages": [{"role": "user", "content": prompt}]},
        **kwargs,
    )


def test_quality_flag_invalid_json_detected():
    """Detects invalid JSON when prompt explicitly asks for JSON output."""
    result = _make_quality_result(
        "List the top 3 cities. Respond in JSON format.",
        "Here are the top 3 cities: New York, London, Tokyo.",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "invalid_json" in flags


def test_quality_flag_valid_json_no_flag():
    """Valid JSON response does not trigger the flag."""
    result = _make_quality_result(
        "List the top 3 cities. Return a JSON array.",
        '["New York", "London", "Tokyo"]',
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "invalid_json" not in flags


def test_quality_flag_json_in_code_block():
    """Valid JSON inside markdown code fences should not trigger the flag."""
    result = _make_quality_result(
        "Give me the config. Output as JSON.",
        '```json\n{"key": "value"}\n```',
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "invalid_json" not in flags


def test_quality_flag_json_not_requested():
    """If JSON is not explicitly requested, don't flag even if response isn't JSON."""
    result = _make_quality_result(
        "Tell me about JSON parsing in Python.",
        "You can use the json module to parse JSON strings.",
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "invalid_json" not in flags


def test_quality_flag_format_bullet_list():
    """Detects missing bullet list when prompt asks for one."""
    result = _make_quality_result(
        "Give me a bullet list of 3 programming languages.",
        "Python is great. JavaScript is popular. Go is fast.",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "format_noncompliant" in flags


def test_quality_flag_format_bullet_list_present():
    """Bullet list present does not trigger the flag."""
    result = _make_quality_result(
        "Give me a bullet list of 3 programming languages.",
        "- Python\n- JavaScript\n- Go",
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "format_noncompliant" not in flags


def test_quality_flag_format_numbered_list():
    """Numbered list accepted for bullet list request."""
    result = _make_quality_result(
        "Give me a bullet list of items.",
        "1. First item\n2. Second item\n3. Third item",
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "format_noncompliant" not in flags


def test_quality_flag_format_code_block():
    """Detects missing code block when prompt asks for one."""
    result = _make_quality_result(
        "Show me a code block with a hello world function.",
        "def hello(): print('hello world')",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "format_noncompliant" in flags


def test_quality_flag_length_too_long():
    """Detects response that is way longer than requested."""
    result = _make_quality_result(
        "Explain gravity in 2 sentences.",
        "Gravity is a force. It pulls things down. It was discovered by Newton. "
        "It affects all objects. The moon orbits Earth because of gravity. "
        "Einstein later refined our understanding. General relativity describes "
        "gravity as spacetime curvature. This was confirmed by observations.",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "length_noncompliant" in flags


def test_quality_flag_length_ok():
    """Response matching the requested length does not trigger the flag."""
    result = _make_quality_result(
        "Explain gravity in 2 sentences.",
        "Gravity is a force that attracts objects toward each other. It keeps planets in orbit around the sun.",
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "length_noncompliant" not in flags


def test_quality_flag_wrong_language():
    """Detects script mismatch between Latin prompt and CJK response."""
    result = _make_quality_result(
        "Tell me about the history of computing in detail please.",
        "\u8ba1\u7b97\u673a\u7684\u5386\u53f2\u53ef\u4ee5\u8ffd\u6eaf\u5230\u53e4\u4ee3\u7684\u7b97\u76d8\u548c\u8ba1\u7b97\u5de5\u5177\u3002"
        "\u73b0\u4ee3\u8ba1\u7b97\u673a\u7684\u53d1\u5c55\u59cb\u4e8e\u4e8c\u5341\u4e16\u7eaa\u3002",
    )
    flags = _compute_quality_flags(result)
    assert flags is not None
    assert "wrong_language" in flags


def test_quality_flag_same_language_no_flag():
    """Same script in prompt and response does not trigger the flag."""
    result = _make_quality_result(
        "Tell me about Python programming.",
        "Python is a high-level programming language known for its readability.",
    )
    flags = _compute_quality_flags(result)
    assert flags is None or "wrong_language" not in flags


def test_quality_flag_short_text_no_language_flag():
    """Very short texts should not trigger language mismatch."""
    result = _make_quality_result("Hi", "OK")
    flags = _compute_quality_flags(result)
    assert flags is None or "wrong_language" not in flags
