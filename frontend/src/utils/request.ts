import axios, { type AxiosRequestConfig, type Canceler } from 'axios'
import { message } from 'ant-design-vue'

// 请求缓存配置
const requestCache = new Map<string, { data: any; timestamp: number }>()
const CACHE_EXPIRE_TIME = 5 * 60 * 1000 // 缓存有效期5分钟

// 取消重复请求配置
const pendingRequest = new Map<string, Canceler>()

// 生成请求唯一key
const generateRequestKey = (config: AxiosRequestConfig): string => {
  const { url, method, params, data } = config
  let dataStr = ''
  if (data instanceof FormData) {
    // 对于FormData，使用特殊处理，避免JSON.stringify返回"{}"
    dataStr = 'FormData-' + Array.from(data.entries()).map(([key, value]) => {
      if (value instanceof File) {
        return `${key}=${value.name}`
      }
      return `${key}=${value}`
    }).join('&')
  } else {
    dataStr = JSON.stringify(data)
  }
  return [url || '', method || '', JSON.stringify(params), dataStr].join('&')
}

// 添加pending请求
const addPendingRequest = (config: AxiosRequestConfig) => {
  if (!config) return
  try {
    const requestKey = generateRequestKey(config)
    (config as any).cancelToken = config.cancelToken || new axios.CancelToken((cancel) => {
      if (!pendingRequest.has(requestKey)) {
        pendingRequest.set(requestKey, cancel)
      }
    })
  } catch (error) {
    console.error('Add pending request error:', error)
  }
}

// 移除pending请求
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
  // Base URL for the API
  baseURL: '/api/v1',
  timeout: 60000 // Increased timeout to 60s for AI generation requests
})

request.interceptors.request.use(
  (config) => {
    // 移除重复请求
    removePendingRequest(config)
    addPendingRequest(config)

    // GET请求缓存处理（排除auth和users/me等关键接口）
    try {
      const isAuthRequest = config.url?.includes('/auth')
      const isMeRequest = config.url?.includes('/users/me')
      const isCacheable = config.method?.toLowerCase() === 'get' && !config.headers?.['Cache-Control'] && !isAuthRequest && !isMeRequest
      
      if (isCacheable) {
        const cacheKey = generateRequestKey(config)
        const cached = requestCache.get(cacheKey)
        if (cached && Date.now() - cached.timestamp < CACHE_EXPIRE_TIME) {
          // 命中缓存，直接返回，包装成AxiosResponse格式
          return Promise.resolve({
            data: cached.data,
            status: 200,
            statusText: 'OK',
            headers: {},
            config
          } as any)
        }
      }
    } catch (error) {
      console.error('Cache check error:', error)
    }

    const token = localStorage.getItem('token')
    if (token) {
      if (!config.headers) {
        (config as any).headers = {}
      }
      (config.headers as any).Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    // 请求完成，移除pending记录
    removePendingRequest(response.config)

    // 缓存GET请求结果
    try {
      if (response.config.method?.toLowerCase() === 'get' && !response.config.headers?.['Cache-Control']) {
        const cacheKey = generateRequestKey(response.config)
        requestCache.set(cacheKey, {
          data: response.data,
          timestamp: Date.now()
        })
      }
    } catch (error) {
      console.error('Cache set error:', error)
    }

    return response
  },
  (error) => {
    // 请求错误，移除pending记录
    if (error.config) {
      removePendingRequest(error.config)
    }

    // 忽略取消请求的错误
    if (axios.isCancel(error)) {
      return Promise.reject(new Error('请求被取消'))
    }

    if (error.response) {
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        if (!window.location.pathname.includes('/auth/login')) {
             message.error('会话已过期，请重新登录')
             window.location.href = '/auth/login'
        }
      } else if (error.response.status >= 500) {
        // 开发环境才打印详细错误
        if (import.meta.env.DEV) {
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

// 手动清除缓存方法
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
