"""
Seed data for the 4 built-in user profiles.

Each profile includes:
- Behavior defaults (session mode, think time, turns)
- Conversation templates with starter prompts
- Follow-up prompts (template-specific and universal)
- Template variables for combinatorial diversity
"""

# ---------------------------------------------------------------------------
# Code snippets for the Programmer profile's $CODE_BLOCK variable.
# Each snippet is 30-100 lines of realistic, reviewable code.
# ---------------------------------------------------------------------------

_SNIPPET_PYTHON_REST_API = """\
from flask import Flask, request, jsonify, g
import sqlite3
import hashlib
import os
from functools import wraps
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production"
DATABASE = "app.db"

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def hash_password(password):
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + hashed.hex()

def verify_password(stored, password):
    salt_hex, hash_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return hashed.hex() == hash_hex

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            g.current_user = data["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username taken"}), 409
    hashed = hash_password(password)
    db.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
               (username, hashed, datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({"message": "User created"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?",
                      (data.get("username"),)).fetchone()
    if not user or not verify_password(user["password_hash"], data.get("password", "")):
        return jsonify({"error": "Invalid credentials"}), 401
    token = jwt.encode(
        {"user_id": user["id"], "exp": datetime.utcnow() + timedelta(hours=24)},
        app.config["SECRET_KEY"], algorithm="HS256"
    )
    return jsonify({"token": token})

@app.route("/items", methods=["GET"])
@token_required
def list_items():
    db = get_db()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    offset = (page - 1) * per_page
    items = db.execute("SELECT * FROM items WHERE user_id = ? LIMIT ? OFFSET ?",
                       (g.current_user, per_page, offset)).fetchall()
    total = db.execute("SELECT COUNT(*) FROM items WHERE user_id = ?",
                       (g.current_user,)).fetchone()[0]
    return jsonify({"items": [dict(i) for i in items], "total": total})\
"""

_SNIPPET_JS_DASHBOARD = """\
import React, { useState, useEffect, useCallback } from 'react';

export default function OrderDashboard() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortField, setSortField] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 25;

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(), per_page: perPage.toString(),
        sort: sortField, dir: sortDir,
        ...(search && { q: search }),
        ...(statusFilter !== 'all' && { status: statusFilter }),
      });
      const res = await fetch(`/api/v1/orders?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setOrders(json.data);
      setTotal(json.meta.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [page, sortField, sortDir, search, statusFilter]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const handleSort = useCallback((field) => {
    setSortField(prev => {
      if (prev === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
      else setSortDir('asc');
      return field;
    });
    setPage(1);
  }, []);

  const totalPages = Math.ceil(total / perPage);
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="dashboard">
      <div className="controls">
        <input type="text" placeholder="Search orders..." value={search}
               onChange={e => { setSearch(e.target.value); setPage(1); }} />
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
          {['all', 'pending', 'shipped', 'delivered', 'cancelled'].map(s => (
            <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s}</option>
          ))}
        </select>
      </div>
      {loading ? <div>Loading...</div> : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                {['id', 'customer', 'amount', 'status', 'date'].map(col => (
                  <th key={col} onClick={() => handleSort(col)}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id}>
                  <td>{o.id}</td>
                  <td>{o.customer_name}</td>
                  <td>${o.amount.toFixed(2)}</td>
                  <td><span className={`badge badge-${o.status}`}>{o.status}</span></td>
                  <td>{new Date(o.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
            <span>Page {page}/{totalPages} ({total})</span>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}"""

_SNIPPET_PYTHON_CACHE = """\
import time
import threading
import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

class LRUCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        while True:
            time.sleep(self.ttl / 2)
            self._evict_expired()

    def _evict_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, (_, ts) in self._store.items() if now - ts > self.ttl]
            for k in expired:
                del self._store[k]
            if expired:
                logger.debug(f"Evicted {len(expired)} expired entries")

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                value, timestamp = self._store[key]
                if time.time() - timestamp <= self.ttl:
                    self._store.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    del self._store[key]
            self._misses += 1
            return None

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, time.time())
            while len(self._store) > self.max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug(f"LRU evicted: {evicted_key}")

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
        }


def cached(cache: LRUCache, key_prefix: str = ""):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            raw_key = f"{key_prefix}:{func.__name__}:{json.dumps(args, default=str)}:{json.dumps(kwargs, default=str, sort_keys=True)}"
            cache_key = hashlib.md5(raw_key.encode()).hexdigest()
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            return result
        return wrapper
    return decorator"""

_SNIPPET_TS_EVENT_SYSTEM = """\
type EventHandler<T = any> = (data: T) => void | Promise<void>;

interface Subscription {
  id: string;
  event: string;
  handler: EventHandler;
  once: boolean;
  priority: number;
}

class EventBus {
  private subs: Map<string, Subscription[]> = new Map();
  private idCounter = 0;
  private history: Array<{ event: string; data: any; ts: number }> = [];
  private maxHistory = 100;

  on<T>(event: string, handler: EventHandler<T>, priority = 0): () => void {
    const sub: Subscription = {
      id: `sub_${++this.idCounter}`,
      event, handler, once: false, priority,
    };
    const list = this.subs.get(event) || [];
    list.push(sub);
    list.sort((a, b) => b.priority - a.priority);
    this.subs.set(event, list);
    return () => this.off(sub.id);
  }

  once<T>(event: string, handler: EventHandler<T>, priority = 0): () => void {
    const sub: Subscription = {
      id: `sub_${++this.idCounter}`,
      event, handler, once: true, priority,
    };
    const list = this.subs.get(event) || [];
    list.push(sub);
    list.sort((a, b) => b.priority - a.priority);
    this.subs.set(event, list);
    return () => this.off(sub.id);
  }

  off(subscriptionId: string): void {
    for (const [event, list] of this.subs) {
      const filtered = list.filter(s => s.id !== subscriptionId);
      if (filtered.length !== list.length) {
        this.subs.set(event, filtered);
        return;
      }
    }
  }

  async emit<T>(event: string, data: T): Promise<void> {
    this.history.push({ event, data, ts: Date.now() });
    if (this.history.length > this.maxHistory) {
      this.history = this.history.slice(-this.maxHistory);
    }

    const handlers = this.subs.get(event) || [];
    const wildcards = this.subs.get('*') || [];
    const all = [...handlers, ...wildcards];
    const toRemove: string[] = [];

    for (const sub of all) {
      try {
        await sub.handler(data);
      } catch (err) {
        console.error(`Handler ${sub.id} for '${event}' threw:`, err);
      }
      if (sub.once) toRemove.push(sub.id);
    }
    for (const id of toRemove) this.off(id);
  }

  listenerCount(event: string): number {
    return (this.subs.get(event) || []).length;
  }

  getHistory(event?: string) {
    return event ? this.history.filter(h => h.event === event) : [...this.history];
  }

  removeAllListeners(event?: string): void {
    event ? this.subs.delete(event) : this.subs.clear();
  }
}

export const eventBus = new EventBus();"""

_SNIPPET_GO_WORKER_POOL = """\
package worker

import (
\t"context"
\t"fmt"
\t"log"
\t"sync"
\t"sync/atomic"
\t"time"
)

type Job struct {
\tID      string
\tPayload interface{}
}

type Result struct {
\tJobID    string
\tOutput   interface{}
\tErr      error
\tDuration time.Duration
}

type Pool struct {
\tworkers   int
\tjobs      chan Job
\tresults   chan Result
\twg        sync.WaitGroup
\tprocessed atomic.Int64
\tfailed    atomic.Int64
\thandler   func(context.Context, Job) (interface{}, error)
\tctx       context.Context
\tcancel    context.CancelFunc
}

func New(workers, buf int, handler func(context.Context, Job) (interface{}, error)) *Pool {
\tctx, cancel := context.WithCancel(context.Background())
\treturn &Pool{
\t\tworkers: workers, jobs: make(chan Job, buf),
\t\tresults: make(chan Result, buf), handler: handler,
\t\tctx: ctx, cancel: cancel,
\t}
}

func (p *Pool) Start() {
\tfor i := 0; i < p.workers; i++ {
\t\tp.wg.Add(1)
\t\tgo p.work(i)
\t}
}

func (p *Pool) work(id int) {
\tdefer p.wg.Done()
\tfor {
\t\tselect {
\t\tcase <-p.ctx.Done():
\t\t\treturn
\t\tcase job, ok := <-p.jobs:
\t\t\tif !ok {
\t\t\t\treturn
\t\t\t}
\t\t\tstart := time.Now()
\t\t\toutput, err := p.handler(p.ctx, job)
\t\t\tdur := time.Since(start)
\t\t\tif err != nil {
\t\t\t\tp.failed.Add(1)
\t\t\t\tlog.Printf("worker %d: job %s failed: %v", id, job.ID, err)
\t\t\t} else {
\t\t\t\tp.processed.Add(1)
\t\t\t}
\t\t\tp.results <- Result{JobID: job.ID, Output: output, Err: err, Duration: dur}
\t\t}
\t}
}

func (p *Pool) Submit(job Job) error {
\tselect {
\tcase <-p.ctx.Done():
\t\treturn fmt.Errorf("pool is shutting down")
\tcase p.jobs <- job:
\t\treturn nil
\t}
}

func (p *Pool) Results() <-chan Result { return p.results }

func (p *Pool) Shutdown() {
\tclose(p.jobs)
\tp.wg.Wait()
\tclose(p.results)
\tlog.Printf("shutdown: %d ok, %d failed", p.processed.Load(), p.failed.Load())
}

func (p *Pool) Cancel() {
\tp.cancel()
\tp.Shutdown()
}"""

_SNIPPET_PYTHON_PIPELINE = """\
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

@dataclass
class PipelineContext:
    data: Any = None
    metadata: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    should_stop: bool = False

class Stage(ABC):
    def __init__(self, name: str, skip_on_error: bool = False):
        self.name = name
        self.skip_on_error = skip_on_error

    @abstractmethod
    def process(self, ctx: PipelineContext) -> PipelineContext:
        pass

class FunctionStage(Stage):
    def __init__(self, name: str, func, skip_on_error: bool = False):
        super().__init__(name, skip_on_error)
        self.func = func

    def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.data = self.func(ctx.data, ctx.metadata)
        return ctx

class ParallelStage(Stage):
    def __init__(self, name: str, stages: list[Stage], max_workers: int = 4):
        super().__init__(name)
        self.stages = stages
        self.max_workers = max_workers

    def process(self, ctx: PipelineContext) -> PipelineContext:
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(s.process, PipelineContext(
                    data=ctx.data, metadata=dict(ctx.metadata)
                )): s for s in self.stages
            }
            for fut in as_completed(futures):
                stage = futures[fut]
                try:
                    r = fut.result()
                    results[stage.name] = r.data
                    ctx.errors.extend(r.errors)
                except Exception as e:
                    ctx.errors.append(f"{stage.name}: {e}")
        ctx.metadata["parallel_results"] = results
        return ctx

class Pipeline:
    def __init__(self, name: str):
        self.name = name
        self.stages: list[Stage] = []

    def add_stage(self, stage: Stage) -> "Pipeline":
        self.stages.append(stage)
        return self

    def run(self, initial_data: Any = None, metadata: dict = None) -> PipelineContext:
        ctx = PipelineContext(data=initial_data, metadata=metadata or {})
        logger.info(f"Pipeline '{self.name}': {len(self.stages)} stages")
        t0 = time.time()
        for stage in self.stages:
            if ctx.should_stop:
                logger.warning(f"Stopped before '{stage.name}'")
                break
            if stage.skip_on_error and ctx.errors:
                logger.info(f"Skipping '{stage.name}' due to prior errors")
                continue
            start = time.time()
            try:
                ctx = stage.process(ctx)
                ctx.timings[stage.name] = round(time.time() - start, 4)
            except Exception as e:
                ctx.timings[stage.name] = round(time.time() - start, 4)
                ctx.errors.append(f"'{stage.name}' failed: {e}")
                logger.error(f"Stage '{stage.name}' failed: {e}")
        ctx.timings["_total"] = round(time.time() - t0, 4)
        logger.info(f"Pipeline done in {ctx.timings['_total']:.3f}s, {len(ctx.errors)} errors")
        return ctx"""

PROFILES = [
    # -------------------------------------------------------
    # 1. Casual User
    # -------------------------------------------------------
    {
        "slug": "casual-user",
        "name": "Casual User",
        "description": "Short conversational prompts, 1-3 turn sessions. Simulates everyday users asking quick questions, getting recommendations, or having brief chats.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 1, "max": 3},
            "think_time_seconds": {"min": 3, "max": 15},
            "sessions_per_user": {"min": 1, "max": 5},
            "read_time_factor": 0.01,
        },
        "conversation_templates": [
            {
                "category": "question",
                "starter_prompt": "What's the difference between $TOPIC_A and $TOPIC_B?",
                "expected_response_tokens": {"min": 80, "max": 250},
                "follow_ups": [
                    {"content": "Can you give me a simple example?"},
                    {"content": "Which one would you recommend for a beginner?"},
                ],
            },
            {
                "category": "recommendation",
                "starter_prompt": "I'm looking for a good $ITEM_TYPE for $PURPOSE. Any suggestions?",
                "expected_response_tokens": {"min": 100, "max": 300},
                "follow_ups": [
                    {"content": "What about something cheaper?"},
                    {"content": "How does that compare to $ALTERNATIVE?"},
                ],
            },
            {
                "category": "explanation",
                "starter_prompt": "Explain $CONCEPT to me like I'm 10 years old.",
                "expected_response_tokens": {"min": 100, "max": 250},
                "follow_ups": [
                    {"content": "Why does that matter?"},
                    {"content": "Can you give a real-world example?"},
                ],
            },
            {
                "category": "how-to",
                "starter_prompt": "How do I $TASK?",
                "expected_response_tokens": {"min": 80, "max": 300},
                "follow_ups": [
                    {"content": "What if that doesn't work?"},
                    {"content": "Is there an easier way?"},
                ],
            },
            {
                "category": "opinion",
                "starter_prompt": "What do you think about $OPINION_TOPIC?",
                "expected_response_tokens": {"min": 80, "max": 250},
                "follow_ups": [
                    {"content": "That's interesting. What are the downsides though?"},
                    {"content": "Would you say most people agree with that?"},
                ],
            },
            {
                "category": "trivia",
                "starter_prompt": "Tell me something interesting about $TRIVIA_SUBJECT.",
                "expected_response_tokens": {"min": 60, "max": 200},
                "follow_ups": [
                    {"content": "Wow, I didn't know that. Tell me more."},
                    {"content": "Where can I learn more about this?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Thanks! One more question — can you summarize that in one sentence?",
            "Interesting. Tell me more.",
            "Wait, I'm confused. Can you rephrase that?",
            "OK got it, thanks!",
        ],
        "template_variables": [
            {"name": "TOPIC_A", "values": ["machine learning", "Python", "REST APIs", "cloud computing", "Docker", "SQL", "Wi-Fi 6", "SSDs", "electric cars", "streaming services"]},
            {"name": "TOPIC_B", "values": ["deep learning", "JavaScript", "GraphQL", "edge computing", "Kubernetes", "NoSQL", "Wi-Fi 7", "NVMe drives", "hybrid cars", "cable TV"]},
            {"name": "CONCEPT", "values": ["blockchain", "quantum computing", "neural networks", "DNS", "encryption", "how a GPS works", "inflation", "black holes", "photosynthesis", "how Wi-Fi works"]},
            {"name": "ITEM_TYPE", "values": ["laptop", "programming book", "online course", "code editor", "headset", "monitor", "mechanical keyboard", "standing desk", "tablet", "router"]},
            {"name": "PURPOSE", "values": ["learning to code", "remote work", "gaming", "data science", "web development", "productivity", "music production", "video editing", "reading", "college"]},
            {"name": "ALTERNATIVE", "values": ["the previous version", "the open-source option", "the budget option", "what I'm using now", "the Apple version"]},
            {"name": "TASK", "values": ["set up a VPN", "create a budget spreadsheet", "back up my photos", "learn a new language fast", "improve my Wi-Fi signal", "organize my email inbox", "set up two-factor authentication", "transfer files between my phone and PC", "speed up my old laptop"]},
            {"name": "OPINION_TOPIC", "values": ["remote work vs office", "learning to code in 2025", "AI replacing jobs", "electric cars vs gas cars", "mechanical keyboards", "dark mode vs light mode", "tabs vs spaces"]},
            {"name": "TRIVIA_SUBJECT", "values": ["the history of the internet", "space exploration", "the human brain", "ancient Rome", "deep sea creatures", "the invention of computers", "volcanoes", "the Olympics"]},
        ],
    },

    # -------------------------------------------------------
    # 2. Power User / Researcher
    # -------------------------------------------------------
    {
        "slug": "power-user",
        "name": "Power User / Researcher",
        "description": "Long analytical prompts with multi-paragraph responses. Simulates researchers, analysts, and advanced users who need deep, nuanced answers and engage in extended conversations.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 5, "max": 15},
            "think_time_seconds": {"min": 15, "max": 60},
            "sessions_per_user": {"min": 1, "max": 2},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "deep-analysis",
                "starter_prompt": "I'm researching $RESEARCH_TOPIC. Can you provide a comprehensive overview of the current state of the field, including the main schools of thought, key recent developments, and open questions that remain unresolved?",
                "expected_response_tokens": {"min": 400, "max": 1200},
                "follow_ups": [
                    {"content": "What are the strongest counterarguments to the dominant position you described?"},
                    {"content": "Can you trace the historical development of this field? What were the key inflection points?"},
                    {"content": "Which methodological approaches have proven most reliable, and why?"},
                    {"content": "How does this intersect with $RELATED_FIELD? Are there cross-disciplinary insights I should be aware of?"},
                    {"content": "If I only had time to read 3 key papers or books on this, what would you recommend and why?"},
                ],
            },
            {
                "category": "comparison",
                "starter_prompt": "Compare and contrast $FRAMEWORK_A and $FRAMEWORK_B in terms of their theoretical foundations, practical applications, empirical support, and limitations. I need a balanced, scholarly assessment.",
                "expected_response_tokens": {"min": 500, "max": 1500},
                "follow_ups": [
                    {"content": "Which one has more empirical support in real-world settings?"},
                    {"content": "What would a synthesis of both approaches look like?"},
                    {"content": "Are there notable critics of either framework? What are their main objections?"},
                    {"content": "How would you apply each framework to $APPLICATION_CONTEXT?"},
                ],
            },
            {
                "category": "literature-review",
                "starter_prompt": "I'm writing a literature review on $REVIEW_TOPIC. What are the seminal papers and key findings I should be aware of? Please organize them chronologically and note any paradigm shifts.",
                "expected_response_tokens": {"min": 500, "max": 1500},
                "follow_ups": [
                    {"content": "What gaps exist in the current literature that could be addressed by future research?"},
                    {"content": "How has the methodology evolved over time in this field?"},
                    {"content": "Can you suggest a structure for organizing my literature review?"},
                    {"content": "Which findings have been most contested or controversial?"},
                ],
            },
            {
                "category": "strategic-assessment",
                "starter_prompt": "I need a thorough assessment of $STRATEGY_TOPIC. What are the key factors to consider, the trade-offs involved, and what does the evidence suggest about best practices?",
                "expected_response_tokens": {"min": 400, "max": 1200},
                "follow_ups": [
                    {"content": "What are the second-order effects that people often overlook?"},
                    {"content": "Can you model out the best-case and worst-case scenarios?"},
                    {"content": "What would a pragmatic implementation roadmap look like?"},
                    {"content": "Who are the leading practitioners in this area and what do they recommend?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Let me push back on that. Isn't it true that $COUNTERPOINT? How would you reconcile that with your analysis?",
            "Can you provide specific citations or data points to support that claim?",
            "How confident are you in that assessment? What would change your mind?",
            "Summarize the key takeaways from our entire conversation so far.",
            "Given everything we've discussed, what would you recommend as the most productive next steps for my research?",
            "Can you steelman the opposing view?",
        ],
        "template_variables": [
            {"name": "RESEARCH_TOPIC", "values": [
                "transformer architectures in NLP",
                "causal inference in observational studies",
                "the impact of remote work on productivity",
                "microservices vs monolithic architecture trade-offs",
                "zero-knowledge proofs in blockchain",
                "the effectiveness of retrieval-augmented generation",
                "technical debt measurement and management",
                "the reliability of LLM-as-judge evaluation methods",
            ]},
            {"name": "RELATED_FIELD", "values": ["cognitive science", "economics", "systems engineering", "information theory", "organizational psychology", "neuroscience", "philosophy of science"]},
            {"name": "FRAMEWORK_A", "values": ["Bayesian inference", "agile methodology", "actor-critic reinforcement learning", "event-driven architecture", "capability-based security", "domain-driven design"]},
            {"name": "FRAMEWORK_B", "values": ["frequentist statistics", "waterfall methodology", "model-based reinforcement learning", "request-response architecture", "role-based access control", "data-driven design"]},
            {"name": "REVIEW_TOPIC", "values": ["LLM evaluation methods", "distributed consensus algorithms", "human-AI collaboration", "technical debt measurement", "software architecture evolution patterns", "prompt engineering techniques"]},
            {"name": "COUNTERPOINT", "values": ["recent studies show contradictory results", "the sample sizes in those studies were too small", "the methodology has been questioned", "industry practitioners report different outcomes", "the theory doesn't account for real-world constraints"]},
            {"name": "STRATEGY_TOPIC", "values": [
                "adopting a microservices architecture for a mid-size company",
                "migrating from a monolith to microservices",
                "building vs buying a data platform",
                "the long-term viability of open-source business models",
                "implementing an AI-first product strategy",
            ]},
            {"name": "APPLICATION_CONTEXT", "values": ["a fast-growing startup", "a large enterprise migration", "an academic research setting", "a regulated healthcare environment"]},
        ],
    },

    # -------------------------------------------------------
    # 3. Programmer
    # -------------------------------------------------------
    {
        "slug": "programmer",
        "name": "Programmer",
        "description": "Code snippets, debugging sessions, and multi-turn refinement. Simulates developers pasting code and asking for improvements, bug fixes, or explanations.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 3, "max": 10},
            "think_time_seconds": {"min": 10, "max": 60},
            "sessions_per_user": {"min": 1, "max": 3},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "code-review",
                "starter_prompt": "Review this $LANGUAGE code and suggest improvements for readability, performance, and best practices:\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "Can you refactor it using the improvements you suggested? Show me the full updated code."},
                    {"content": "What about error handling? What edge cases am I missing?"},
                    {"content": "How would you write unit tests for this?"},
                    {"content": "Can you add type hints and docstrings?"},
                ],
            },
            {
                "category": "debugging",
                "starter_prompt": "I'm getting an unexpected result from this $LANGUAGE code. The expected output is $EXPECTED_OUTPUT but I'm getting $ACTUAL_OUTPUT. Can you find the bug?\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "That fixed it, but now I'm seeing a performance issue with large inputs. How can I optimize it?"},
                    {"content": "Can you explain why the original code produced the wrong result?"},
                    {"content": "Are there any other potential issues you can spot?"},
                ],
            },
            {
                "category": "implementation",
                "starter_prompt": "Write a $LANGUAGE implementation of $ALGORITHM_OR_FEATURE. It should handle $REQUIREMENTS.",
                "expected_response_tokens": {"min": 300, "max": 1000},
                "follow_ups": [
                    {"content": "Can you add error handling and input validation?"},
                    {"content": "How would you modify this to be thread-safe?"},
                    {"content": "Can you write a version that's more memory-efficient?"},
                    {"content": "Now add logging and make it production-ready."},
                ],
            },
            {
                "category": "explanation",
                "starter_prompt": "Explain what this $LANGUAGE code does step by step. I inherited this from a colleague and need to understand it before modifying it:\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "What design pattern is this using? Is it the right choice here?"},
                    {"content": "If I needed to add $NEW_FEATURE to this, where would I start?"},
                    {"content": "What would break if I removed the $COMPONENT part?"},
                ],
            },
            {
                "category": "architecture",
                "starter_prompt": "I'm building $PROJECT_DESC in $LANGUAGE. What's a good project structure and architecture for this? Give me the key files and how they connect.",
                "expected_response_tokens": {"min": 300, "max": 1000},
                "follow_ups": [
                    {"content": "Can you write the boilerplate for the main entry point?"},
                    {"content": "How should I handle configuration and environment variables?"},
                    {"content": "What about testing? What's the test structure?"},
                    {"content": "How would I add $NEW_FEATURE later without major refactoring?"},
                ],
            },
            {
                "category": "convert",
                "starter_prompt": "Convert this $LANGUAGE code to $ALT_LANGUAGE. Keep the same logic but use idiomatic patterns for the target language:\n\n```$LANGUAGE\n$CODE_BLOCK\n```",
                "expected_response_tokens": {"min": 200, "max": 800},
                "follow_ups": [
                    {"content": "Are there any gotchas I should watch out for with this conversion?"},
                    {"content": "Can you also add the equivalent package imports and setup?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Can you add comments explaining the non-obvious parts?",
            "What's the time and space complexity of this solution?",
            "Show me an alternative approach.",
            "How would this look in $ALT_LANGUAGE instead?",
            "Can you write a quick benchmark to compare the two approaches?",
        ],
        "template_variables": [
            {"name": "LANGUAGE", "values": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"]},
            {"name": "ALT_LANGUAGE", "values": ["Python", "Go", "Rust", "TypeScript"]},
            {"name": "EXPECTED_OUTPUT", "values": ["a sorted list", "True", "the sum of all values", "a valid JSON object", "an HTTP 200 response"]},
            {"name": "ACTUAL_OUTPUT", "values": ["an empty list", "False", "None", "a TypeError", "an HTTP 500 response", "an infinite loop"]},
            {"name": "ALGORITHM_OR_FEATURE", "values": [
                "a rate limiter using token bucket",
                "a LRU cache",
                "a retry mechanism with exponential backoff",
                "a connection pool",
                "a simple pub/sub event system",
                "a CLI argument parser",
                "a file watcher that detects changes",
                "a concurrent task queue with priorities",
            ]},
            {"name": "REQUIREMENTS", "values": ["concurrent access from multiple threads", "graceful error recovery", "configurable timeouts", "memory usage under 100MB", "sub-millisecond lookup time", "safe shutdown on SIGTERM"]},
            {"name": "NEW_FEATURE", "values": ["caching", "retry logic", "authentication", "pagination", "streaming support", "rate limiting", "logging", "metrics collection"]},
            {"name": "COMPONENT", "values": ["the middleware", "the validation layer", "the callback", "the context manager", "the decorator", "the abstract base class"]},
            {"name": "PROJECT_DESC", "values": [
                "a REST API with user auth and CRUD operations",
                "a CLI tool for managing database migrations",
                "a WebSocket server for real-time chat",
                "a background job processor with retry logic",
                "a web scraper with rate limiting",
            ]},
            {"name": "CODE_BLOCK", "values": [
                _SNIPPET_PYTHON_REST_API,
                _SNIPPET_JS_DASHBOARD,
                _SNIPPET_PYTHON_CACHE,
                _SNIPPET_TS_EVENT_SYSTEM,
                _SNIPPET_GO_WORKER_POOL,
                _SNIPPET_PYTHON_PIPELINE,
            ]},
        ],
    },

    # -------------------------------------------------------
    # 4. Data Analyst
    # -------------------------------------------------------
    {
        "slug": "data-analyst",
        "name": "Data Analyst",
        "description": "CSV/table data, SQL generation, analysis requests, and data interpretation. Simulates analysts who work with structured data and need query help or statistical insights.",
        "behavior_defaults": {
            "session_mode": "multi_turn",
            "turns_per_session": {"min": 3, "max": 8},
            "think_time_seconds": {"min": 10, "max": 45},
            "sessions_per_user": {"min": 1, "max": 3},
            "read_time_factor": 0.03,
        },
        "conversation_templates": [
            {
                "category": "sql-query",
                "starter_prompt": "I have a $DATABASE_TYPE database with the following tables:\n\n$SCHEMA_DESCRIPTION\n\nWrite a SQL query to $QUERY_GOAL.",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "How would I optimize this query for a table with 50 million rows?"},
                    {"content": "Can you add a window function to also show the running total?"},
                    {"content": "Now modify it to filter by date range and group by $GROUP_BY."},
                    {"content": "Explain the query plan — where might this be slow?"},
                ],
            },
            {
                "category": "data-interpretation",
                "starter_prompt": "I have the following dataset summary:\n\n$DATA_SUMMARY\n\nWhat are the key insights? What patterns or anomalies do you see? Suggest 3 analyses I should run next.",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "How would I test if the trend you identified is statistically significant?"},
                    {"content": "Write Python code using pandas to reproduce this analysis."},
                    {"content": "What visualizations would best communicate these findings to a non-technical stakeholder?"},
                    {"content": "Are there any confounding variables I should control for?"},
                ],
            },
            {
                "category": "data-transformation",
                "starter_prompt": "I need to transform $SOURCE_FORMAT data into $TARGET_FORMAT. The source data looks like this:\n\n$SAMPLE_DATA\n\nWrite a $TRANSFORM_LANGUAGE script to do the transformation.",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "How do I handle missing values and data quality issues?"},
                    {"content": "Add validation to ensure the output matches the expected schema."},
                    {"content": "Now make this work as a scheduled pipeline that runs daily."},
                ],
            },
            {
                "category": "metrics-design",
                "starter_prompt": "I'm building a dashboard to track $DASHBOARD_GOAL. What KPIs and metrics should I include? How should I define each one precisely so my team can implement them?",
                "expected_response_tokens": {"min": 300, "max": 800},
                "follow_ups": [
                    {"content": "Can you write the SQL for the 3 most important metrics?"},
                    {"content": "What would good vs bad look like for each metric? Give me benchmark ranges."},
                    {"content": "How often should each metric be refreshed?"},
                    {"content": "What alerts should I set up based on these metrics?"},
                ],
            },
            {
                "category": "statistical-analysis",
                "starter_prompt": "I have two groups of $STAT_SUBJECT and I want to know if the difference between them is statistically significant. Group A ($STAT_N_A samples): mean=$STAT_MEAN_A, std=$STAT_STD_A. Group B ($STAT_N_B samples): mean=$STAT_MEAN_B, std=$STAT_STD_B. What test should I use and how do I interpret the results?",
                "expected_response_tokens": {"min": 200, "max": 600},
                "follow_ups": [
                    {"content": "Can you write the Python code to run this test using scipy?"},
                    {"content": "What if my data isn't normally distributed?"},
                    {"content": "How large would my sample need to be to detect a 5% difference with 80% power?"},
                ],
            },
        ],
        "universal_follow_ups": [
            "Can you add error handling for edge cases like null values and duplicates?",
            "How would I set this up to run automatically on a schedule?",
            "Summarize the methodology so I can include it in my report.",
            "Can you export this as a reusable function I can call from other scripts?",
        ],
        "template_variables": [
            {"name": "DATABASE_TYPE", "values": ["PostgreSQL", "MySQL", "BigQuery", "Snowflake", "SQLite"]},
            {"name": "SCHEMA_DESCRIPTION", "values": [
                "- users (id, name, email, created_at, plan_type)\n- orders (id, user_id, amount, status, created_at)\n- products (id, name, category, price)",
                "- events (id, user_id, event_type, properties JSONB, timestamp)\n- sessions (id, user_id, start_time, end_time, device_type)\n- users (id, signup_date, country, tier)",
                "- customers (id, name, region, segment, created_at)\n- invoices (id, customer_id, total, status, issued_at, paid_at)\n- line_items (id, invoice_id, product_id, quantity, unit_price)",
            ]},
            {"name": "QUERY_GOAL", "values": [
                "find the top 10 customers by total spend in the last 90 days",
                "calculate monthly retention cohorts",
                "identify users who downgraded their plan after a support ticket",
                "find products frequently bought together",
                "compute the rolling 7-day average of daily active users",
                "find the median time between first signup and first purchase",
            ]},
            {"name": "GROUP_BY", "values": ["month", "category", "region", "user tier", "device type", "day of week"]},
            {"name": "DATA_SUMMARY", "values": [
                "Monthly revenue: Jan $120K, Feb $135K, Mar $128K, Apr $142K, May $155K, Jun $148K. Churn rate has been increasing from 3.2% to 4.1% over the same period. Average deal size decreased from $2,400 to $2,100.",
                "We tracked 50,000 API requests over 24 hours. Median latency: 45ms. P95: 280ms. P99: 1,200ms. Error rate: 2.3%. Peak traffic at 2PM UTC (3x baseline). 68% of errors are timeouts, 22% are 429s, 10% are 500s.",
                "A/B test results after 2 weeks: Control (n=5,000): 3.2% conversion, $45 avg order. Variant (n=5,100): 3.8% conversion, $42 avg order. Bounce rate: Control 62%, Variant 58%.",
            ]},
            {"name": "SOURCE_FORMAT", "values": ["CSV", "JSON", "nested JSON API responses", "Excel", "Parquet"]},
            {"name": "TARGET_FORMAT", "values": ["a normalized PostgreSQL schema", "a flat CSV for analysis", "a Parquet file for analytics", "a JSON API response format"]},
            {"name": "SAMPLE_DATA", "values": [
                "id,name,orders\n1,Alice,\"[{product: 'A', qty: 2}, {product: 'B', qty: 1}]\"\n2,Bob,\"[{product: 'C', qty: 5}]\"",
                "{\"users\": [{\"id\": 1, \"name\": \"Alice\", \"address\": {\"city\": \"NYC\", \"zip\": \"10001\"}, \"tags\": [\"premium\", \"active\"]}, {\"id\": 2, \"name\": \"Bob\", \"address\": {\"city\": \"LA\", \"zip\": \"90001\"}, \"tags\": [\"free\"]}]}",
            ]},
            {"name": "TRANSFORM_LANGUAGE", "values": ["Python", "SQL", "dbt", "pandas"]},
            {"name": "DASHBOARD_GOAL", "values": [
                "SaaS product health (signups, activation, retention, revenue)",
                "API performance and reliability for our platform team",
                "e-commerce conversion funnel from landing page to purchase",
                "customer support team efficiency and satisfaction",
            ]},
            {"name": "STAT_SUBJECT", "values": ["response times", "conversion rates", "user session durations", "error rates"]},
            {"name": "STAT_N_A", "values": ["150", "500", "1200"]},
            {"name": "STAT_N_B", "values": ["145", "480", "1180"]},
            {"name": "STAT_MEAN_A", "values": ["42.3", "0.032", "8.5"]},
            {"name": "STAT_MEAN_B", "values": ["38.7", "0.041", "9.2"]},
            {"name": "STAT_STD_A", "values": ["12.1", "0.008", "3.2"]},
            {"name": "STAT_STD_B", "values": ["11.8", "0.009", "3.5"]},
        ],
    },
]
