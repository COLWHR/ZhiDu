const storageKeys = {
  apiBaseUrl: 'zhido_api_base_url',
  accessToken: 'zhido_access_token',
  refreshToken: 'zhido_refresh_token',
  accessTokenExpiresAt: 'zhido_access_token_expires_at',
  refreshTokenExpiresAt: 'zhido_refresh_token_expires_at',
  user: 'zhido_user',
}

const DEFAULT_API_BASE_URL = 'https://zhuanerzhuxue.cn/api/v1'
const PRODUCTION_SITE_URL = 'https://zhuanerzhuxue.cn'
const PRODUCTION_WS_BASE_URL = 'wss://zhuanerzhuxue.cn/api/v1'
const PRODUCTION_API_BASE_URL = DEFAULT_API_BASE_URL

function normalizeBaseUrl(url) {
  return String(url || '').trim().replace(/\/$/, '')
}

function isValidApiBaseUrl(url) {
  const normalized = normalizeBaseUrl(url)
  return normalized === PRODUCTION_API_BASE_URL
}

function loadApiBaseUrl() {
  const stored = normalizeBaseUrl(wx.getStorageSync(storageKeys.apiBaseUrl))
  if (isValidApiBaseUrl(stored)) {
    return stored
  }

  if (stored) {
    wx.setStorageSync(storageKeys.apiBaseUrl, DEFAULT_API_BASE_URL)
  }

  return DEFAULT_API_BASE_URL
}

let apiBaseUrl = loadApiBaseUrl()

function getApiBaseUrl() {
  return apiBaseUrl
}

function getServerOrigin() {
  return PRODUCTION_SITE_URL
}

function getWsBaseUrl() {
  return PRODUCTION_WS_BASE_URL
}

function setApiBaseUrl(url) {
  const normalized = normalizeBaseUrl(url)
  apiBaseUrl = isValidApiBaseUrl(normalized) ? normalized : DEFAULT_API_BASE_URL
  wx.setStorageSync(storageKeys.apiBaseUrl, apiBaseUrl)
}

module.exports = {
  DEFAULT_API_BASE_URL,
  apiBaseUrl,
  getApiBaseUrl,
  getServerOrigin,
  getWsBaseUrl,
  normalizeBaseUrl,
  setApiBaseUrl,
  storageKeys,
}
