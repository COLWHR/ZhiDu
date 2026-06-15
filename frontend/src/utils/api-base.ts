const DEFAULT_PROD_API_BASE_URL = 'https://zhuanerzhuxue.cn/api/v1'
const DEFAULT_PROD_WS_BASE_URL = 'wss://zhuanerzhuxue.cn'

const normalizeTrailingSlash = (value: string) => value.replace(/\/+$/, '')

const normalizeHttpBase = (value: string) => {
  const trimmed = String(value || '').trim()
  if (!trimmed) return ''
  return normalizeTrailingSlash(trimmed)
}

const normalizeWsBase = (value: string) => {
  const trimmed = String(value || '').trim()
  if (!trimmed) return ''

  if (trimmed.startsWith('http://')) {
    return normalizeTrailingSlash(trimmed.replace(/^http:/, 'ws:'))
  }

  if (trimmed.startsWith('https://')) {
    return normalizeTrailingSlash(trimmed.replace(/^https:/, 'wss:'))
  }

  return normalizeTrailingSlash(trimmed)
}

export const resolveApiBaseUrl = () => {
  const envBase = normalizeHttpBase(import.meta.env.VITE_API_BASE_URL as string | undefined)
  if (envBase) return envBase

  if (import.meta.env.PROD) {
    return DEFAULT_PROD_API_BASE_URL
  }

  return '/api/v1'
}

export const resolveWsBaseUrl = () => {
  const envBase = normalizeWsBase(import.meta.env.VITE_WS_BASE_URL as string | undefined)
  if (envBase) return envBase

  if (import.meta.env.PROD) {
    return DEFAULT_PROD_WS_BASE_URL
  }

  if (typeof window === 'undefined') {
    return DEFAULT_PROD_WS_BASE_URL
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

