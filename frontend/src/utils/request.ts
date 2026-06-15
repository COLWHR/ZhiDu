import axios, { type AxiosRequestConfig, type AxiosResponse, type Canceler } from 'axios'
import { message } from 'ant-design-vue'
import { getActivePinia } from 'pinia'
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  isAccessTokenExpiringSoon,
  isRefreshTokenValid,
  normalizeAuthTokenPayload,
  saveAuthSession,
} from './auth-session'

const requestCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_EXPIRE_TIME = 5 * 60 * 1000
const pendingRequest = new Map<string, Canceler>()
let refreshPromise: Promise<boolean> | null = null

type RetryableAxiosConfig = AxiosRequestConfig & { _retry?: boolean }

type CachedResponseError = Error & {
  __fromCache?: boolean
  cachedResponse?: AxiosResponse
}

const generateRequestKey = (config: AxiosRequestConfig, token: string = ''): string => {
  const { url, method, params, data } = config
  let dataStr = ''

  if (data instanceof FormData) {
    dataStr = 'FormData-' + Array.from(data.entries()).map(([key, value]) => {
      if (value instanceof File) {
        return `${key}=${value.name}`
      }
      return `${key}=${value}`
    }).join('&')
  } else {
    dataStr = JSON.stringify(data)
  }

  return [url || '', method || '', token, JSON.stringify(params), dataStr].join('&')
}

const addPendingRequest = (config: AxiosRequestConfig) => {
  if (!config) return

  try {
    const requestKey = generateRequestKey(config)
    ;(config as any).cancelToken = config.cancelToken || new axios.CancelToken((cancel) => {
      if (!pendingRequest.has(requestKey)) {
        pendingRequest.set(requestKey, cancel)
      }
    })
  } catch (error) {
    console.error('Add pending request error:', error)
  }
}

const removePendingRequest = (config: AxiosRequestConfig) => {
  if (!config) return

  try {
    const requestKey = generateRequestKey(config)
    if (pendingRequest.has(requestKey)) {
      const cancel = pendingRequest.get(requestKey)
      cancel?.(requestKey)
      pendingRequest.delete(requestKey)
    }
  } catch (error) {
    console.error('Remove pending request error:', error)
  }
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

const syncAuthStoreFromStorage = async () => {
  if (!getActivePinia()) {
    return
  }

  try {
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    authStore.syncSessionFromStorage()
  } catch (error) {
    console.error('Failed to sync auth store:', error)
  }
}

const clearAuthState = async () => {
  clearAuthSession()
  clearRequestCache()

  if (!getActivePinia()) {
    return
  }

  try {
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    authStore.clearSession()
  } catch (error) {
    console.error('Failed to clear auth store:', error)
  }
}

const refreshAuthSession = async (): Promise<boolean> => {
  if (!isRefreshTokenValid()) {
    return false
  }

  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        return false
      }

      const response = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      })

      const normalized = normalizeAuthTokenPayload(response.data)
      if (!normalized.access_token || !normalized.refresh_token) {
        throw new Error('Invalid refresh response')
      }

      saveAuthSession(normalized, undefined)
      await syncAuthStoreFromStorage()
      return true
    })().finally(() => {
      refreshPromise = null
    })
  }

  return refreshPromise
}

const isAuthEndpoint = (url?: string) => Boolean(url && url.includes('/auth'))

request.interceptors.request.use(
  async (config) => {
    removePendingRequest(config)
    addPendingRequest(config)

    const token = getAccessToken()
    const shouldRefresh = Boolean(token) && !isAuthEndpoint(config.url) && isAccessTokenExpiringSoon(60)

    if (shouldRefresh) {
      try {
        await refreshAuthSession()
      } catch (error) {
        console.warn('Proactive refresh failed:', error)
      }
    }

    const currentToken = getAccessToken()
    try {
      const isMeRequest = config.url?.includes('/users/me')
      const isCacheable =
        config.method?.toLowerCase() === 'get' &&
        !config.headers?.['Cache-Control'] &&
        !isAuthEndpoint(config.url) &&
        !isMeRequest

      if (isCacheable) {
        const cacheKey = generateRequestKey(config, currentToken)
        const cached = requestCache.get(cacheKey)

        if (cached && Date.now() - cached.timestamp < CACHE_EXPIRE_TIME) {
          const cachedResponse = {
            data: cached.data,
            status: 200,
            statusText: 'OK',
            headers: {},
            config,
          } as AxiosResponse

          const cachedError = new Error('cached-response') as CachedResponseError
          cachedError.__fromCache = true
          cachedError.cachedResponse = cachedResponse
          return Promise.reject(cachedError)
        }
      }
    } catch (error) {
      console.error('Cache check error:', error)
    }

    if (currentToken) {
      if (!config.headers) {
        ;(config as any).headers = {}
      }
      ;(config.headers as any).Authorization = `Bearer ${currentToken}`
    }

    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    removePendingRequest(response.config)

    try {
      if (response.config.method?.toLowerCase() === 'get' && !response.config.headers?.['Cache-Control']) {
        const token = getAccessToken()
        const cacheKey = generateRequestKey(response.config, token)
        requestCache.set(cacheKey, {
          data: response.data,
          timestamp: Date.now(),
        })
      }
    } catch (error) {
      console.error('Cache set error:', error)
    }

    return response
  },
  async (error) => {
    if (error?.__fromCache && error.cachedResponse) {
      removePendingRequest(error.cachedResponse.config)
      return Promise.resolve(error.cachedResponse)
    }

    if (error.config) {
      removePendingRequest(error.config)
    }

    if (axios.isCancel(error)) {
      return Promise.reject(new Error('请求已取消'))
    }

    if (error.response) {
      if (error.response.status === 401) {
        const originalConfig = error.config as RetryableAxiosConfig | undefined
        const canRetry = originalConfig && !originalConfig._retry && !isAuthEndpoint(originalConfig.url)

        if (canRetry && isRefreshTokenValid()) {
          originalConfig._retry = true
          try {
            const refreshed = await refreshAuthSession()
            if (refreshed) {
              const newToken = getAccessToken()
              const retryConfig: RetryableAxiosConfig = {
                ...originalConfig,
                headers: {
                  ...(originalConfig.headers || {}),
                  Authorization: `Bearer ${newToken}`,
                },
              }
              delete (retryConfig as any).cancelToken
              delete (retryConfig as any).signal
              return request(retryConfig)
            }
          } catch (refreshError) {
            console.warn('Token refresh failed:', refreshError)
          }
        }

        await clearAuthState()
        message.error('会话已过期，请重新登录')
        if (import.meta.env.MODE !== 'test' && !window.location.pathname.includes('/auth/login')) {
          window.location.href = '/auth/login'
        }
      } else if (error.response.status >= 500) {
        if (import.meta.env.DEV && import.meta.env.MODE !== 'test') {
          console.error('Server Error:', JSON.stringify(error.response.data, null, 2))
        }
        message.error('服务器内部错误，请稍后重试')
      } else {
        const detail = error.response.data?.detail
        const msg = typeof detail === 'string' ? detail : (detail?.message || '请求失败')
        message.error(msg)
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络设置')
    } else {
      message.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

export const clearRequestCache = (pattern?: string) => {
  if (!pattern) {
    requestCache.clear()
    return
  }

  requestCache.forEach((_, key) => {
    if (key.includes(pattern)) {
      requestCache.delete(key)
    }
  })
}

export default request
