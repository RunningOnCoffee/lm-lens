import asyncio
import json
import os
import random
import time
import uuid

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="LM Lens Mock LLM")

LATENCY_MS = int(os.getenv("MOCK_LLM_LATENCY_MS", "200"))
TOKENS_PER_SECOND = int(os.getenv("MOCK_LLM_TOKENS_PER_SECOND", "50"))

WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "I",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over",
    "think", "also", "back", "after", "use", "two", "how", "our", "work",
    "first", "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "great", "between", "need", "large", "often",
]


def generate_response_text(prompt_tokens: int) -> str:
    """Generate a plausible-length response based on input size."""
    # Roughly 0.5x to 2x the input length
    output_words = random.randint(max(10, prompt_tokens // 3), max(20, prompt_tokens * 2))
    words = []
    for i in range(output_words):
        word = random.choice(WORDS)
        if i == 0 or random.random() < 0.08:
            word = word.capitalize()
        words.append(word)
        if random.random() < 0.12:
            words.append(".")
    return " ".join(words)


def count_tokens(text: str) -> int:
    """Rough token estimate: ~0.75 tokens per word."""
    return max(1, int(len(text.split()) * 0.75))


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "mock-llm"
    messages: list[Message]
    max_tokens: int | None = None
    temperature: float = 1.0
    stream: bool = False


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mock-llm"}


@app.get("/v1/models")
async def list_models():
    return {
        "data": [
            {"id": "mock-llm", "object": "model", "owned_by": "lm-lens"}
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    prompt_text = " ".join(m.content for m in request.messages)
    prompt_tokens = count_tokens(prompt_text)
    response_text = generate_response_text(prompt_tokens)
    output_tokens = count_tokens(response_text)

    # Enforce max_tokens: truncate response if limit is set
    finish_reason = "stop"
    if request.max_tokens is not None and output_tokens > request.max_tokens:
        words = response_text.split()
        # Truncate to approximate max_tokens (tokens ≈ words * 0.75)
        max_words = max(1, int(request.max_tokens / 0.75))
        response_text = " ".join(words[:max_words])
        output_tokens = request.max_tokens
        finish_reason = "length"

    # Simulate TTFT latency
    ttft_seconds = LATENCY_MS / 1000.0 * random.uniform(0.8, 1.2)
    await asyncio.sleep(ttft_seconds)

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    if request.stream:
        return StreamingResponse(
            _stream_response(completion_id, response_text, output_tokens, prompt_tokens, finish_reason),
            media_type="text/event-stream",
        )

    # Non-streaming: simulate full generation time
    gen_time = output_tokens / TOKENS_PER_SECOND
    await asyncio.sleep(gen_time)

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
        },
    }


async def _stream_response(completion_id: str, text: str, output_tokens: int, prompt_tokens: int, finish_reason: str = "stop"):
    """Stream tokens at the configured rate."""
    words = text.split()
    tokens_sent = 0
    delay = 1.0 / TOKENS_PER_SECOND

    for i, word in enumerate(words):
        chunk_content = word if i == 0 else f" {word}"
        chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "mock-llm",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": chunk_content},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        tokens_sent += 1
        await asyncio.sleep(delay * random.uniform(0.7, 1.3))

    # Final chunk
    final = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "mock-llm",
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": tokens_sent,
            "total_tokens": prompt_tokens + tokens_sent,
        },
    }
    yield f"data: {json.dumps(final)}\n\n"
    yield "data: [DONE]\n\n"
