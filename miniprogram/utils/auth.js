const { storageKeys } = require('./config')

function normalizeAuthTokenPayload(payload) {
  return {
    access_token: payload && payload.access_token ? payload.access_token : '',
    refresh_token: payload && payload.refresh_token ? payload.refresh_token : '',
    token_type: payload && payload.token_type ? payload.token_type : 'bearer',
    access_token_expires_at: payload && payload.access_token_expires_at ? payload.access_token_expires_at : '',
    refresh_token_expires_at: payload && payload.refresh_token_expires_at ? payload.refresh_token_expires_at : '',
  }
}

function saveSession(payload, user) {
  const normalized = normalizeAuthTokenPayload(payload || {})
  wx.setStorageSync(storageKeys.accessToken, normalized.access_token)
  wx.setStorageSync(storageKeys.refreshToken, normalized.refresh_token)
  wx.setStorageSync(storageKeys.accessTokenExpiresAt, normalized.access_token_expires_at)
  wx.setStorageSync(storageKeys.refreshTokenExpiresAt, normalized.refresh_token_expires_at)

  if (user !== undefined) {
    if (user) {
      wx.setStorageSync(storageKeys.user, user)
    } else {
      wx.removeStorageSync(storageKeys.user)
    }
  }

  return normalized
}

function readSession() {
  return {
    accessToken: wx.getStorageSync(storageKeys.accessToken) || '',
    refreshToken: wx.getStorageSync(storageKeys.refreshToken) || '',
    accessTokenExpiresAt: wx.getStorageSync(storageKeys.accessTokenExpiresAt) || '',
    refreshTokenExpiresAt: wx.getStorageSync(storageKeys.refreshTokenExpiresAt) || '',
    user: wx.getStorageSync(storageKeys.user) || null,
  }
}

function clearSession() {
  wx.removeStorageSync(storageKeys.accessToken)
  wx.removeStorageSync(storageKeys.refreshToken)
  wx.removeStorageSync(storageKeys.accessTokenExpiresAt)
  wx.removeStorageSync(storageKeys.refreshTokenExpiresAt)
  wx.removeStorageSync(storageKeys.user)
}

function setUser(user) {
  if (user) {
    wx.setStorageSync(storageKeys.user, user)
  } else {
    wx.removeStorageSync(storageKeys.user)
  }
}

function getAccessToken() {
  return wx.getStorageSync(storageKeys.accessToken) || ''
}

function getRefreshToken() {
  return wx.getStorageSync(storageKeys.refreshToken) || ''
}

function parseDate(value) {
  if (!value) return 0
  const ts = Date.parse(value)
  return Number.isFinite(ts) ? ts : 0
}

function isRefreshTokenValid() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  const expiresAt = parseDate(wx.getStorageSync(storageKeys.refreshTokenExpiresAt))
  if (!expiresAt) return true
  return expiresAt > Date.now()
}

function isAccessTokenExpiringSoon(seconds) {
  const expiresAt = parseDate(wx.getStorageSync(storageKeys.accessTokenExpiresAt))
  if (!expiresAt) return false
  const threshold = Number(seconds || 60) * 1000
  return expiresAt - Date.now() <= threshold
}

module.exports = {
  clearSession,
  getAccessToken,
  getRefreshToken,
  isAccessTokenExpiringSoon,
  isRefreshTokenValid,
  normalizeAuthTokenPayload,
  readSession,
  saveSession,
  setUser,
}
