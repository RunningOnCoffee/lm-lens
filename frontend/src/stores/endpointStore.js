import { create } from 'zustand';
import { endpointsApi } from '../api/client';

const useEndpointStore = create((set, get) => ({
  endpoints: [],
  loading: false,
  error: null,

  fetchEndpoints: async () => {
    set({ loading: true, error: null });
    try {
      const res = await endpointsApi.list();
      set({ endpoints: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  deleteEndpoint: async (id) => {
    await endpointsApi.delete(id);
    set({ endpoints: get().endpoints.filter((e) => e.id !== id) });
  },

  cloneEndpoint: async (id) => {
    const res = await endpointsApi.clone(id);
    await get().fetchEndpoints();
    return res.data;
  },
}));

export default useEndpointStore;
