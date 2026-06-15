export interface AuthUser {
  id: number
  username: string
  role: string
}

export interface AuthTokenPayload {
  access_token: string
  refresh_token: string
  token_type?: string
  access_token_expires_at: string
  refresh_token_expires_at: string
}

export interface AuthSession {
  token: string | null
  refreshToken: string | null
  user: AuthUser | null
  accessTokenExpiresAt: string | null
  refreshTokenExpiresAt: string | null
}

const TOKEN_KEY = 'token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_KEY = 'user'
const ACCESS_TOKEN_EXPIRES_AT_KEY = 'token_expires_at'
const REFRESH_TOKEN_EXPIRES_AT_KEY = 'refresh_token_expires_at'

const safeParse = <T>(value: string | null, fallback: T): T => {
  if (!value) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}

export const readAuthSession = (): AuthSession => ({
  token: localStorage.getItem(TOKEN_KEY),
  refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  user: safeParse<AuthUser | null>(localStorage.getItem(USER_KEY), null),
  accessTokenExpiresAt: localStorage.getItem(ACCESS_TOKEN_EXPIRES_AT_KEY),
  refreshTokenExpiresAt: localStorage.getItem(REFRESH_TOKEN_EXPIRES_AT_KEY),
})

export const saveAuthSession = (payload: AuthTokenPayload, user?: AuthUser | null) => {
  localStorage.setItem(TOKEN_KEY, payload.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, payload.refresh_token)
  localStorage.setItem(ACCESS_TOKEN_EXPIRES_AT_KEY, payload.access_token_expires_at)
  localStorage.setItem(REFRESH_TOKEN_EXPIRES_AT_KEY, payload.refresh_token_expires_at)

  if (user !== undefined) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }
}

export const clearAuthSession = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(ACCESS_TOKEN_EXPIRES_AT_KEY)
  localStorage.removeItem(REFRESH_TOKEN_EXPIRES_AT_KEY)
}

export const setAuthUser = (user: AuthUser | null) => {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export const getAccessToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY) || ''
export const getStoredUser = () => safeParse<AuthUser | null>(localStorage.getItem(USER_KEY), null)

export const isSessionExpired = (expiresAt: string | null, graceSeconds = 0) => {
  if (!expiresAt) return true
  const expiry = Date.parse(expiresAt)
  if (Number.isNaN(expiry)) return true
  return Date.now() >= expiry - graceSeconds * 1000
}

export const isAccessTokenExpiringSoon = (graceSeconds = 60) => {
  const expiresAt = localStorage.getItem(ACCESS_TOKEN_EXPIRES_AT_KEY)
  if (!expiresAt) return false
  return isSessionExpired(expiresAt, graceSeconds)
}

export const isRefreshTokenValid = () => {
  const expiresAt = localStorage.getItem(REFRESH_TOKEN_EXPIRES_AT_KEY)
  if (!expiresAt) return false
  return !isSessionExpired(expiresAt, 0)
}

export const normalizeAuthTokenPayload = (payload: any): AuthTokenPayload => {
  const accessToken = String(payload?.access_token || '')
  const refreshToken = String(payload?.refresh_token || '')
  const accessExpires = String(payload?.access_token_expires_at || '')
  const refreshExpires = String(payload?.refresh_token_expires_at || '')

  return {
    access_token: accessToken,
    refresh_token: refreshToken,
    token_type: String(payload?.token_type || 'bearer'),
    access_token_expires_at: accessExpires,
    refresh_token_expires_at: refreshExpires,
  }
}
