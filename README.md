# LM Lens

**Realistic LLM performance benchmarking for any OpenAI-compatible endpoint.**

LM Lens simulates multi-user workloads with realistic conversation patterns to stress-test LLM inference servers. Instead of firing uniform requests, it models different user archetypes — casual chatters, power researchers, programmers pasting code, data analysts querying tables — each with distinct prompt lengths, turn counts, and think times.

Run it against llama.cpp, vLLM, Ollama, LM Studio, OpenAI, or any OpenAI-compatible API.

## Features

- **User Profile Simulation** — 4 built-in profiles (Casual User, Power User, Programmer, Data Analyst) with multi-turn conversations, variable substitution, and realistic think/read times. Create custom profiles for your workloads.
- **Three Test Modes** — Stress Test (full load), Ramp Up (gradual users), Breaking Point (auto-detect failure thresholds for TTFT, ITL, and error rate).
- **Load Curves** — Step, Linear, Spike, and Wave patterns with visual preview in the scenario builder.
- **Live Dashboard** — Real-time WebSocket metrics: TTFT timeline, throughput charts, per-profile latency breakdown, request log, progress tracking.
- **Prefill/Decode Analysis** — Token economy chart with Tokens/Time/Speed views showing GPU time split between prefill (prompt processing) and decode (token generation) phases per profile.
- **Quality Scoring** — Heuristic quality evaluation across 4 dimensions (completeness, compliance, coherence, safety) with per-request quality flags (truncated, empty, refusal, repeated tokens).
- **A/B Comparison** — Side-by-side benchmark comparison with delta percentages, quality diffs, and per-profile breakdown.
- **Response Browser** — Session-grouped conversation viewer with chat-style bubbles, per-turn metrics, ITL sparklines, and quality flag pills.
- **Export** — Download results as CSV or JSON for offline analysis.
- **Safety Rails** — Configurable max concurrency cap, graceful abort (preserves collected data), error capture as data.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────>│   Backend    │────>│  PostgreSQL   │
│  React/Vite  │<────│   FastAPI    │<────│    16         │
│  Nginx :8090 │     │     :8080    │     │    :5433      │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                            │ HTTP/SSE
                            v
                     ┌──────────────┐
                     │  LLM Server  │
                     │  (any OAI-   │
                     │  compatible) │
                     └──────────────┘
```

| Service | Tech | Port |
|---------|------|------|
| Frontend | React 18, Vite, Tailwind CSS, Recharts | 8090 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), httpx | 8080 |
| Database | PostgreSQL 16, asyncpg | 5433 |
| Mock LLM | FastAPI mock OpenAI API (for testing without a real LLM) | 8081 |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/LMLens.git
cd LMLens
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up --build -d
```

This starts the database, backend (with auto-migrations and seed data), frontend, and mock LLM server.

### 3. Open the UI

Navigate to **http://localhost:8090**

### 4. Run your first benchmark

1. Go to **AI Endpoints** and add your LLM server (or use the built-in mock at `http://lm-lens-mock:8000`)
2. Go to **Scenarios** and create a test scenario — pick profiles, set user counts, choose a test mode
3. Go to **Benchmarks**, select your scenario and endpoint, and hit **Start**
4. Watch live metrics on the dashboard

## Connecting to LLM Endpoints

Since requests are made from inside Docker, use these URLs:

| LLM Location | Endpoint URL |
|---|---|
| Built-in mock server | `http://lm-lens-mock:8000` |
| Local LLM on host (llama.cpp, vLLM, Ollama, LM Studio) | `http://host.docker.internal:PORT` |
| LLM on another machine on the network | `http://<MACHINE_IP>:PORT` |
| Cloud API (OpenAI, Together, etc.) | `https://api.openai.com` (+ API key) |

The `/v1/chat/completions` path is appended automatically. Use **Test Connection** in the UI to verify.

## Metrics Collected

| Metric | Description |
|--------|-------------|
| TTFT | Time to First Token — measures prefill/prompt processing latency |
| TGT | Total Generation Time — end-to-end request duration |
| ITL | Inter-Token Latency — time between consecutive tokens (decode speed) |
| tok/s | Tokens per second — generation throughput |
| Input/Output Tokens | Token counts per request, aggregated per profile |
| Prefill/Decode Speed | tok/s during each inference phase (input processing vs output generation) |
| Quality Scores | Per-dimension scores (completeness, compliance, coherence, safety) |
| Quality Flags | Truncated, empty, refusal, repeated tokens — detected per response |

## Test Modes

- **Stress Test** — All virtual users active simultaneously for the full duration
- **Ramp Up** — Gradually add users over time (configurable step size and interval)
- **Breaking Point** — Ramp up until failure criteria are breached (TTFT, inter-token latency, or error rate thresholds)

## Development

```bash
# Rebuild and restart
docker compose up --build -d

# Tail logs
docker compose logs -f

# Run backend tests
docker compose exec lm-lens-api pytest -v

# Open database shell
docker compose exec lm-lens-db psql -U lm-lens -d lm-lens

# Full reset (destroys all data)
docker compose down -v && docker compose up --build -d
```

## Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, httpx, asyncpg, Pydantic v2

**Frontend:** React 18, Vite 5, Tailwind CSS 3, Recharts, Zustand, TanStack Table, React Router v6

**Infrastructure:** Docker Compose, PostgreSQL 16, Nginx

## License

MIT
