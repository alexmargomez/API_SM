const API_BASE = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'api_sm_token'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

async function request(endpoint, options = {}) {
  const token = getStoredToken()
  const headers = {
    ...(options.headers || {}),
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Token ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.error || data.detail || 'Error en la petición al servidor.')
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

export const apiService = {
  getStats() {
    return request('/panel/stats/')
  },

  getEntidades(params = {}) {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.regimen) query.set('regimen', params.regimen)
    if (params.page) query.set('page', String(params.page))
    const qs = query.toString()
    return request(`/panel/entidades/${qs ? `?${qs}` : ''}`)
  },

  getCie10(params = {}) {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.page) query.set('page', String(params.page))
    const qs = query.toString()
    return request(`/panel/cie10/${qs ? `?${qs}` : ''}`)
  },

  getCups(params = {}) {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.page) query.set('page', String(params.page))
    const qs = query.toString()
    return request(`/panel/cups/${qs ? `?${qs}` : ''}`)
  },

  getExportUrl(entity) {
    return `${API_BASE}/panel/export/${entity}/`
  },

  uploadCatalog(type, file) {
    const formData = new FormData()
    formData.append('type', type)
    formData.append('file', file)
    return request('/panel/import/', {
      method: 'POST',
      body: formData,
    })
  },

  login(username, password) {
    return request('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  logout() {
    return request('/auth/logout/', {
      method: 'POST',
    })
  },

  me() {
    return request('/auth/me/')
  },
}
