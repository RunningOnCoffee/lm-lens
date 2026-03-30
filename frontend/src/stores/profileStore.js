import { create } from 'zustand';
import { profilesApi } from '../api/client';

const useProfileStore = create((set, get) => ({
  profiles: [],
  loading: false,
  error: null,

  fetchProfiles: async () => {
    set({ loading: true, error: null });
    try {
      const res = await profilesApi.list();
      set({ profiles: res.data, loading: false });
    } catch (err) {
      set({ error: err.message, loading: false });
    }
  },

  deleteProfile: async (id) => {
    await profilesApi.delete(id);
    set({ profiles: get().profiles.filter((p) => p.id !== id) });
  },

  cloneProfile: async (id) => {
    const res = await profilesApi.clone(id);
    await get().fetchProfiles();
    return res.data;
  },
}));

export default useProfileStore;
