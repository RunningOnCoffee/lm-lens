import { useState, useEffect } from 'react';

function StatusCard({ label, value, status }) {
  const statusColor = {
    healthy: 'text-green-400',
    error: 'text-danger',
    loading: 'text-gray-500',
  };

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-semibold ${statusColor[status] || 'text-gray-200'}`}>
        {value}
      </p>
    </div>
  );
}

export default function Dashboard() {
  const [health, setHealth] = useState({ api: 'loading', db: 'loading', mock: 'loading' });

  useEffect(() => {
    fetch('/api/v1/health')
      .then((r) => r.json())
      .then((data) => {
        const c = data.data.components;
        setHealth({
          api: data.data.status === 'healthy' ? 'healthy' : 'error',
          db: c.database,
          mock: c.mock_llm === 'healthy' ? 'healthy' : 'error',
        });
      })
      .catch(() => setHealth({ api: 'error', db: 'error', mock: 'error' }));
  }, []);

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatusCard label="API Server" value={health.api} status={health.api} />
        <StatusCard label="Mock LLM" value={health.mock} status={health.mock} />
        <StatusCard label="Benchmarks Run" value="0" status="healthy" />
      </div>
      <div className="bg-surface-800 border border-surface-600 rounded-xl p-8 text-center">
        <p className="text-gray-400 font-heading text-lg mb-2">Ready to benchmark</p>
        <p className="text-gray-600 text-sm">
          Create a scenario to start testing your LLM endpoint performance.
        </p>
      </div>
    </div>
  );
}
