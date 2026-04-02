import { useEffect, useRef, useCallback, useState } from 'react';

/**
 * Hook for connecting to a benchmark's live WebSocket.
 * Accumulates snapshots into an array for time-series charts.
 */
export default function useWebSocket(benchmarkId, { enabled = true } = {}) {
  const [snapshots, setSnapshots] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (!benchmarkId || !enabled) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/api/v1/benchmarks/${benchmarkId}/live`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const snapshot = JSON.parse(event.data);
        setSnapshots((prev) => [...prev, snapshot]);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 2s if still enabled
      if (enabled) {
        reconnectTimer.current = setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [benchmarkId, enabled]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const reset = useCallback(() => setSnapshots([]), []);

  return { snapshots, connected, reset };
}
