import { reactive } from 'vue'
import { apiService, getStoredToken, setStoredToken } from '../services/api'

const USER_KEY = 'api_sm_user'

function loadStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const authState = reactive({
  user: loadStoredUser(),
  isAuthenticated: Boolean(getStoredToken() && loadStoredUser()),
  flashMessage: null,
  flashType: 'info',
})

export function setFlash(message, type = 'info') {
  authState.flashMessage = message
  authState.flashType = type
}

export function clearFlash() {
  authState.flashMessage = null
}

export async function loginAdmin(username, password) {
  const response = await apiService.login(username, password)
  setStoredToken(response.token)
  localStorage.setItem(USER_KEY, JSON.stringify(response.user))
  authState.user = response.user
  authState.isAuthenticated = true
  setFlash(response.message || `¡Bienvenido de nuevo, ${response.user.username}!`, 'success')
  return response
}

export async function logoutAdmin() {
  try {
    await apiService.logout()
  } catch {
    // Ignorar error si el token ya expiró
  } finally {
    setStoredToken(null)
    localStorage.removeItem(USER_KEY)
    authState.user = null
    authState.isAuthenticated = false
    setFlash('Has cerrado sesión exitosamente.', 'info')
  }
}

export async function verifySession() {
  const token = getStoredToken()
  if (!token) {
    authState.user = null
    authState.isAuthenticated = false
    return false
  }
  try {
    const response = await apiService.me()
    authState.user = response.user
    authState.isAuthenticated = true
    localStorage.setItem(USER_KEY, JSON.stringify(response.user))
    return true
  } catch {
    setStoredToken(null)
    localStorage.removeItem(USER_KEY)
    authState.user = null
    authState.isAuthenticated = false
    return false
  }
}
