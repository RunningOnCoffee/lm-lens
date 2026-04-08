from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class LLMRequestResult:
    """Structured result from a single LLM API call."""

    success: bool = False
    ttft_ms: float | None = None
    tgt_ms: float | None = None
    inter_token_latencies: list[float] = field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    tokens_per_second: float | None = None
    http_status: int | None = None
    error_type: str | None = None
    error_detail: str | None = None
    model_reported: str | None = None
    response_text: str = ""
    request_body: dict | None = None
    finish_reason: str | None = None


def _normalize_url(endpoint_url: str) -> str:
    """Build the full chat completions URL from a base endpoint."""
    url = endpoint_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        if not url.endswith("/v1"):
            url += "/v1"
        url += "/chat/completions"
    return url


def _estimate_tokens(text: str) -> int:
    """Rough token estimate when usage stats are unavailable."""
    return max(1, int(len(text.split()) * 1.33))


class LLMClient:
    """Async client for OpenAI-compatible chat completions with metric capture."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str | None,
        model_name: str,
        llm_params: dict,
        *,
        stream: bool = True,
        connect_timeout: float = 30.0,
        read_timeout: float = 120.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = _normalize_url(endpoint_url)
        self._model = model_name
        self._llm_params = llm_params
        self._stream = stream

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(connect_timeout, read=read_timeout),
            )
            self._owns_client = True

    def _build_body(self, messages: list[dict]) -> dict:
        body: dict = {
            "model": self._model,
            "messages": [m.copy() for m in messages],
            "stream": self._stream,
        }
        # Add LLM params, skipping None/empty values
        for key in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
            val = self._llm_params.get(key)
            if val is not None:
                body[key] = val
        max_tokens = self._llm_params.get("max_tokens")
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        stop = self._llm_params.get("stop")
        if stop:
            body["stop"] = stop
        return body

    async def send(self, messages: list[dict]) -> LLMRequestResult:
        body = self._build_body(messages)
        result = LLMRequestResult(request_body=body)
        try:
            if self._stream:
                await self._send_streaming(body, result)
            else:
                await self._send_non_streaming(body, result)
        except httpx.TimeoutException as exc:
            result.error_type = "timeout"
            result.error_detail = str(exc)
        except httpx.ConnectError as exc:
            result.error_type = "connection"
            result.error_detail = str(exc)
        except httpx.HTTPError as exc:
            result.error_type = "connection"
            result.error_detail = str(exc)
        except Exception as exc:
            result.error_type = "parse_error"
            result.error_detail = str(exc)
        return result

    async def _send_streaming(self, body: dict, result: LLMRequestResult) -> None:
        t0 = time.perf_counter()
        first_token_received = False
        prev_token_time: float | None = None
        chunks: list[str] = []

        async with self._client.stream("POST", self._url, json=body) as resp:
            result.http_status = resp.status_code
            if resp.status_code >= 400:
                error_body = ""
                async for chunk in resp.aiter_text():
                    error_body += chunk
                result.success = False
                result.error_type = f"http_{resp.status_code // 100}xx"
                result.error_detail = error_body[:500]
                result.tgt_ms = (time.perf_counter() - t0) * 1000
                return

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue

                payload = line[6:].strip()
                if payload == "[DONE]":
                    break

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                now = time.perf_counter()

                # Extract content delta
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        if not first_token_received:
                            result.ttft_ms = (now - t0) * 1000
                            first_token_received = True
                        elif prev_token_time is not None:
                            result.inter_token_latencies.append(
                                (now - prev_token_time) * 1000
                            )
                        prev_token_time = now
                        chunks.append(content)

                    # Check for finish_reason with usage in final chunk
                    finish = choices[0].get("finish_reason")
                    if finish:
                        result.finish_reason = finish
                        usage = data.get("usage")
                        if usage:
                            result.input_tokens = usage.get("prompt_tokens")
                            result.output_tokens = usage.get("completion_tokens")

                # Usage may also be at top level on final chunk (no choices content)
                if not choices or not choices[0].get("delta", {}).get("content"):
                    usage = data.get("usage")
                    if usage:
                        result.input_tokens = usage.get("prompt_tokens")
                        result.output_tokens = usage.get("completion_tokens")

                result.model_reported = data.get("model", result.model_reported)

        result.tgt_ms = (time.perf_counter() - t0) * 1000
        result.response_text = "".join(chunks)
        result.success = True

        # Fill in token estimates if server didn't report usage
        if result.input_tokens is None:
            prompt_text = " ".join(m.get("content", "") for m in body["messages"])
            result.input_tokens = _estimate_tokens(prompt_text)
        if result.output_tokens is None:
            result.output_tokens = _estimate_tokens(result.response_text) if result.response_text else 0

        # TPS
        if result.output_tokens and result.tgt_ms and result.tgt_ms > 0:
            result.tokens_per_second = result.output_tokens / (result.tgt_ms / 1000)

    async def _send_non_streaming(self, body: dict, result: LLMRequestResult) -> None:
        t0 = time.perf_counter()
        resp = await self._client.post(self._url, json=body)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        result.http_status = resp.status_code
        result.tgt_ms = elapsed_ms
        result.ttft_ms = elapsed_ms  # non-streaming: TTFT = TGT

        if resp.status_code >= 400:
            result.error_type = f"http_{resp.status_code // 100}xx"
            result.error_detail = resp.text[:500]
            return

        try:
            data = resp.json()
        except Exception as exc:
            result.error_type = "parse_error"
            result.error_detail = str(exc)
            return

        result.model_reported = data.get("model")

        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            result.response_text = message.get("content", "")
            result.finish_reason = choices[0].get("finish_reason")

        usage = data.get("usage", {})
        result.input_tokens = usage.get("prompt_tokens")
        result.output_tokens = usage.get("completion_tokens")

        # Fallback token estimates
        if result.input_tokens is None:
            prompt_text = " ".join(m.get("content", "") for m in body["messages"])
            result.input_tokens = _estimate_tokens(prompt_text)
        if result.output_tokens is None:
            result.output_tokens = _estimate_tokens(result.response_text) if result.response_text else 0

        if result.output_tokens and result.tgt_ms and result.tgt_ms > 0:
            result.tokens_per_second = result.output_tokens / (result.tgt_ms / 1000)

        result.success = True

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
