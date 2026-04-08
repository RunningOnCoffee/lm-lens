import { create } from 'zustand';
import { benchmarksApi } from '../api/client';

const useBenchmarkStore = create((set, get) => ({
  benchmarks: [],
  loading: false,
  error: null,

  fetchBenchmarks: async () => {
    set({ loading: true, error: null });
    try {
      const res = await benchmarksApi.list();
      set({ benchmarks: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  startBenchmark: async (scenarioId, endpointId, seed) => {
    const res = await benchmarksApi.start(scenarioId, endpointId, seed);
    await get().fetchBenchmarks();
    return res.data;
  },

  abortBenchmark: async (id) => {
    await benchmarksApi.abort(id);
    await get().fetchBenchmarks();
  },

  deleteBenchmark: async (id) => {
    await benchmarksApi.delete(id);
    set({ benchmarks: get().benchmarks.filter((b) => b.id !== id) });
  },
}));

export default useBenchmarkStore;
