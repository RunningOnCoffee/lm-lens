"""
Realistic code snippets for the Programmer profile.
These get substituted into {{code_block}} template variables.
"""

CODE_SNIPPETS = [
    {
        "language": "Python",
        "pattern": "API endpoint",
        "domain": "web",
        "code": """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI()

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

def get_db():
    conn = sqlite3.connect("users.db")
    return conn

@app.post("/users")
def create_user(user: User):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
                   (user.name, user.email, user.age))
    db.commit()
    user_id = cursor.lastrowid
    db.close()
    return {"id": user_id, "name": user.name}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    db.close()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": row[0], "name": row[1], "email": row[2], "age": row[3]}

@app.get("/users")
def list_users(skip: int = 0, limit: int = 100):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, skip))
    rows = cursor.fetchall()
    db.close()
    return [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]""",
    },
    {
        "language": "JavaScript",
        "pattern": "React component",
        "domain": "frontend",
        "code": """import React, { useState, useEffect } from 'react';

function UserDashboard({ userId }) {
  const [user, setUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/users/${userId}`)
      .then(res => res.json())
      .then(data => {
        setUser(data);
        return fetch(`/api/users/${userId}/orders`);
      })
      .then(res => res.json())
      .then(data => {
        setOrders(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  const totalSpent = orders.reduce((sum, order) => sum + order.amount, 0);

  return (
    <div className="dashboard">
      <h1>Welcome, {user.name}</h1>
      <div className="stats">
        <div>Total Orders: {orders.length}</div>
        <div>Total Spent: ${totalSpent.toFixed(2)}</div>
        <div>Member Since: {new Date(user.createdAt).toLocaleDateString()}</div>
      </div>
      <h2>Recent Orders</h2>
      <table>
        <thead>
          <tr><th>Order ID</th><th>Date</th><th>Amount</th><th>Status</th></tr>
        </thead>
        <tbody>
          {orders.map(order => (
            <tr key={order.id}>
              <td>{order.id}</td>
              <td>{new Date(order.date).toLocaleDateString()}</td>
              <td>${order.amount.toFixed(2)}</td>
              <td>{order.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default UserDashboard;""",
    },
    {
        "language": "Python",
        "pattern": "data processing",
        "domain": "analytics",
        "code": """import csv
from collections import defaultdict
from datetime import datetime

def process_sales_report(filepath):
    sales_by_region = defaultdict(float)
    sales_by_month = defaultdict(float)
    product_counts = defaultdict(int)
    errors = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                amount = float(row['amount'])
                date = datetime.strptime(row['date'], '%Y-%m-%d')
                region = row['region']
                product = row['product']

                sales_by_region[region] += amount
                month_key = date.strftime('%Y-%m')
                sales_by_month[month_key] += amount
                product_counts[product] += 1
            except (ValueError, KeyError) as e:
                errors.append(f"Row {i}: {e}")

    top_regions = sorted(sales_by_region.items(), key=lambda x: x[1], reverse=True)[:5]
    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    monthly_trend = sorted(sales_by_month.items())

    total_revenue = sum(sales_by_region.values())
    avg_monthly = total_revenue / len(sales_by_month) if sales_by_month else 0

    return {
        'total_revenue': total_revenue,
        'avg_monthly_revenue': avg_monthly,
        'top_regions': top_regions,
        'top_products': top_products,
        'monthly_trend': monthly_trend,
        'error_count': len(errors),
        'errors': errors[:10],
    }""",
    },
    {
        "language": "Go",
        "pattern": "HTTP middleware",
        "domain": "web",
        "code": """package middleware

import (
\t"log"
\t"net/http"
\t"sync"
\t"time"
)

type RateLimiter struct {
\tmu       sync.Mutex
\ttokens   map[string]int
\tlimit    int
\tinterval time.Duration
}

func NewRateLimiter(limit int, interval time.Duration) *RateLimiter {
\trl := &RateLimiter{
\t\ttokens:   make(map[string]int),
\t\tlimit:    limit,
\t\tinterval: interval,
\t}
\tgo rl.cleanup()
\treturn rl
}

func (rl *RateLimiter) cleanup() {
\tfor {
\t\ttime.Sleep(rl.interval)
\t\trl.mu.Lock()
\t\tfor k := range rl.tokens {
\t\t\trl.tokens[k] = 0
\t\t}
\t\trl.mu.Unlock()
\t}
}

func (rl *RateLimiter) Allow(key string) bool {
\trl.mu.Lock()
\tdefer rl.mu.Unlock()
\tif rl.tokens[key] >= rl.limit {
\t\treturn false
\t}
\trl.tokens[key]++
\treturn true
}

func (rl *RateLimiter) Middleware(next http.Handler) http.Handler {
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
\t\tip := r.RemoteAddr
\t\tif !rl.Allow(ip) {
\t\t\thttp.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
\t\t\tlog.Printf("Rate limited: %s", ip)
\t\t\treturn
\t\t}
\t\tstart := time.Now()
\t\tnext.ServeHTTP(w, r)
\t\tlog.Printf("%s %s %s %v", r.Method, r.URL.Path, ip, time.Since(start))
\t})
}""",
    },
    {
        "language": "TypeScript",
        "pattern": "state management",
        "domain": "frontend",
        "code": """interface Todo {
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
}

interface TodoState {
  todos: Todo[];
  filter: 'all' | 'active' | 'completed';
}

class TodoStore {
  private state: TodoState = {
    todos: [],
    filter: 'all',
  };
  private listeners: Set<() => void> = new Set();

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach(l => l());
  }

  addTodo(text: string): void {
    const todo: Todo = {
      id: Math.random().toString(36).substr(2, 9),
      text,
      completed: false,
      createdAt: new Date(),
    };
    this.state = {
      ...this.state,
      todos: [...this.state.todos, todo],
    };
    this.notify();
  }

  toggleTodo(id: string): void {
    this.state = {
      ...this.state,
      todos: this.state.todos.map(t =>
        t.id === id ? { ...t, completed: !t.completed } : t
      ),
    };
    this.notify();
  }

  deleteTodo(id: string): void {
    this.state = {
      ...this.state,
      todos: this.state.todos.filter(t => t.id !== id),
    };
    this.notify();
  }

  setFilter(filter: TodoState['filter']): void {
    this.state = { ...this.state, filter };
    this.notify();
  }

  getFilteredTodos(): Todo[] {
    switch (this.state.filter) {
      case 'active':
        return this.state.todos.filter(t => !t.completed);
      case 'completed':
        return this.state.todos.filter(t => t.completed);
      default:
        return this.state.todos;
    }
  }

  getState(): TodoState {
    return this.state;
  }
}

export const todoStore = new TodoStore();""",
    },
    {
        "language": "Python",
        "pattern": "async worker",
        "domain": "backend",
        "code": """import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

@dataclass
class Job:
    id: str
    payload: dict
    retries: int = 0
    max_retries: int = 3

class AsyncWorkerPool:
    def __init__(self, num_workers: int, handler: Callable[[Job], Awaitable[Any]]):
        self.num_workers = num_workers
        self.handler = handler
        self.queue: asyncio.Queue[Job | None] = asyncio.Queue()
        self.results: dict[str, Any] = {}
        self.failed: list[Job] = []
        self._workers: list[asyncio.Task] = []

    async def start(self):
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} workers")

    async def _worker(self, worker_id: int):
        while True:
            job = await self.queue.get()
            if job is None:
                break
            try:
                result = await self.handler(job)
                self.results[job.id] = result
                logger.info(f"Worker {worker_id}: completed job {job.id}")
            except Exception as e:
                logger.error(f"Worker {worker_id}: job {job.id} failed: {e}")
                if job.retries < job.max_retries:
                    job.retries += 1
                    await self.queue.put(job)
                else:
                    self.failed.append(job)
            finally:
                self.queue.task_done()

    async def submit(self, job: Job):
        await self.queue.put(job)

    async def shutdown(self):
        await self.queue.join()
        for _ in self._workers:
            await self.queue.put(None)
        await asyncio.gather(*self._workers)
        logger.info(f"Shutdown complete. {len(self.results)} succeeded, {len(self.failed)} failed")""",
    },
]
