import { create } from 'zustand';
import { scenariosApi } from '../api/client';

const useScenarioStore = create((set, get) => ({
  scenarios: [],
  loading: false,
  error: null,

  fetchScenarios: async () => {
    set({ loading: true, error: null });
    try {
      const res = await scenariosApi.list();
      set({ scenarios: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  deleteScenario: async (id) => {
    await scenariosApi.delete(id);
    set({ scenarios: get().scenarios.filter((s) => s.id !== id) });
  },

  cloneScenario: async (id) => {
    const res = await scenariosApi.clone(id);
    await get().fetchScenarios();
    return res.data;
  },
}));

export default useScenarioStore;
