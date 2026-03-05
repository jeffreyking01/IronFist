import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// Inject JWT token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ironfist_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ironfist_token')
      localStorage.removeItem('ironfist_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  login:  (username, password) =>
    api.post('/auth/local', { username, password }),
  me:     () => api.get('/auth/me'),
  config: () => api.get('/auth/config'),
}

// ── Dashboard ──────────────────────────────────────────────────────────────────
export const dashboardApi = {
  summary: () => api.get('/dashboard/summary'),
}

// ── Assets ─────────────────────────────────────────────────────────────────────
export const assetsApi = {
  list:       (params) => api.get('/assets/', { params }),
  get:        (id)     => api.get(`/assets/${id}`),
  boundaries: ()       => api.get('/assets/stats/boundaries'),
}

// ── Vulnerabilities ────────────────────────────────────────────────────────────
export const vulnsApi = {
  list: (params) => api.get('/vulnerabilities/', { params }),
  kev:  ()       => api.get('/vulnerabilities/kev'),
  get:  (id)     => api.get(`/vulnerabilities/${id}`),
}

// ── Connectors ─────────────────────────────────────────────────────────────────
export const connectorsApi = {
  list: () => api.get('/connectors/'),
}

// ── Sync ───────────────────────────────────────────────────────────────────────
export const syncApi = {
  all:     () => api.post('/sync/all'),
  kev:     () => api.post('/sync/kev'),
  tenable: () => api.post('/sync/tenable'),
}

export default api
