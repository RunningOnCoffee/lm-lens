const BASE_URL = '/api/v1';

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.error?.message || `HTTP ${response.status}`);
  }
  return response.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),
};

// Profiles API
export const profilesApi = {
  list: () => api.get('/profiles'),
  get: (id) => api.get(`/profiles/${id}`),
  create: (body) => api.post('/profiles', body),
  update: (id, body) => api.put(`/profiles/${id}`, body),
  delete: (id) => api.del(`/profiles/${id}`),
  clone: (id) => api.post(`/profiles/${id}/clone`),
  preview: (id) => api.post(`/profiles/${id}/preview`),
};

// Scenarios API
export const scenariosApi = {
  list: () => api.get('/scenarios'),
  get: (id) => api.get(`/scenarios/${id}`),
  create: (body) => api.post('/scenarios', body),
  update: (id, body) => api.put(`/scenarios/${id}`, body),
  delete: (id) => api.del(`/scenarios/${id}`),
  clone: (id) => api.post(`/scenarios/${id}/clone`),
};

// Endpoints API
export const endpointsApi = {
  list: () => api.get('/endpoints'),
  get: (id) => api.get(`/endpoints/${id}`),
  create: (body) => api.post('/endpoints', body),
  update: (id, body) => api.put(`/endpoints/${id}`, body),
  delete: (id) => api.del(`/endpoints/${id}`),
  clone: (id) => api.post(`/endpoints/${id}/clone`),
  testConnection: (body) => api.post('/endpoint/test', body),
};

// Benchmarks API
export const benchmarksApi = {
  list: () => api.get('/benchmarks'),
  get: (id) => api.get(`/benchmarks/${id}`),
  start: (scenarioId, endpointId) => api.post('/benchmarks', { scenario_id: scenarioId, endpoint_id: endpointId }),
  delete: (id) => api.del(`/benchmarks/${id}`),
  abort: (id) => api.post(`/benchmarks/${id}/abort`),
  snapshots: (id) => api.get(`/benchmarks/${id}/snapshots`),
  requests: (id) => api.get(`/benchmarks/${id}/requests`),
};
