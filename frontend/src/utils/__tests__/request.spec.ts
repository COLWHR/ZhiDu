import { describe, it, expect, vi, beforeEach } from 'vitest'
import request, { clearRequestCache } from '../request'
import { server } from '../../mocks/server'
import { http, HttpResponse } from 'msw'
import { message } from 'ant-design-vue'

vi.mock('ant-design-vue', () => ({
  message: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('Request Utility', () => {
  beforeEach(() => {
    clearRequestCache()
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should handle successful responses', async () => {
    const res = await request.get('/users/me')
    expect(res.status).toBe(200)
    expect(res.data.username).toBe('testuser')
  })

  it('should handle 401 Unauthorized by clearing token', async () => {
    server.use(
      http.get('/api/v1/auth-error', () => new HttpResponse(null, { status: 401 }))
    )

    localStorage.setItem('token', 'old-token')

    try {
      await request.get('/auth-error')
    } catch {
      // expected
    }

    expect(localStorage.getItem('token')).toBeNull()
    expect(message.error).toHaveBeenCalledWith('会话已过期，请重新登录')
  })

  it('should refresh an expired access token and retry the original request', async () => {
    let protectedCalls = 0

    server.use(
      http.get('/api/v1/protected', () => {
        protectedCalls += 1
        if (protectedCalls === 1) {
          return new HttpResponse(null, { status: 401 })
        }
        return HttpResponse.json({ ok: true, call: protectedCalls })
      }),
      http.post('/api/v1/auth/refresh', async () => {
        return HttpResponse.json({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          token_type: 'bearer',
          access_token_expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
          refresh_token_expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        })
      })
    )

    localStorage.setItem('token', 'expired-access')
    localStorage.setItem('refresh_token', 'valid-refresh')
    localStorage.setItem('refresh_token_expires_at', new Date(Date.now() + 60 * 60 * 1000).toISOString())

    const res = await request.get('/protected')
    expect(res.data.ok).toBe(true)
    expect(localStorage.getItem('token')).toBe('fresh-access')
    expect(localStorage.getItem('refresh_token')).toBe('fresh-refresh')
    expect(protectedCalls).toBe(2)
  })

  it('should handle 500 Server Errors', async () => {
    server.use(
      http.get('/api/v1/server-error', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Fatal' }), { status: 500 })
      })
    )

    try {
      await request.get('/server-error')
    } catch {
      // expected
    }

    expect(message.error).toHaveBeenCalledWith('服务器内部错误，请稍后重试')
  })

  it('should handle network connection failure', async () => {
    server.use(
      http.get('/api/v1/network-fail', () => HttpResponse.error())
    )

    try {
      await request.get('/network-fail')
    } catch {
      // expected
    }

    expect(message.error).toHaveBeenCalledWith('网络连接失败，请检查网络设置')
  })

  it('should handle general API errors with detail message', async () => {
    server.use(
      http.get('/api/v1/bad-request', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Invalid parameters' }), { status: 400 })
      })
    )

    try {
      await request.get('/bad-request')
    } catch {
      // expected
    }

    expect(message.error).toHaveBeenCalledWith('Invalid parameters')
  })

  it('should handle general API errors with object detail', async () => {
    server.use(
      http.get('/api/v1/bad-request-obj', () => {
        return new HttpResponse(JSON.stringify({ detail: { message: 'Object error' } }), { status: 400 })
      })
    )

    try {
      await request.get('/bad-request-obj')
    } catch {
      // expected
    }

    expect(message.error).toHaveBeenCalledWith('Object error')
  })

  it('should handle request configuration errors', async () => {
    const interceptor = (request.interceptors.response as any).handlers[0].rejected

    try {
      await interceptor({ message: 'config error' })
    } catch {
      // expected
    }

    expect(message.error).toHaveBeenCalledWith('请求配置错误')
  })

  it('should handle request interceptor errors', async () => {
    const interceptor = (request.interceptors.request as any).handlers[0].rejected
    const error = new Error('request config error')

    try {
      await interceptor(error)
    } catch (e) {
      expect(e).toBe(error)
    }
  })

  it('should keep cached GET responses isolated by token', async () => {
    clearRequestCache()

    let callCount = 0
    server.use(
      http.get('/api/v1/token-sensitive', ({ request }) => {
        callCount += 1
        return HttpResponse.json({
          auth: request.headers.get('authorization'),
        })
      })
    )

    localStorage.setItem('token', 'token-a')
    const first = await request.get('/token-sensitive')
    expect(first.data.auth).toBe('Bearer token-a')

    const second = await request.get('/token-sensitive')
    expect(second.data.auth).toBe('Bearer token-a')
    expect(callCount).toBe(1)

    localStorage.setItem('token', 'token-b')
    const third = await request.get('/token-sensitive')
    expect(third.data.auth).toBe('Bearer token-b')
    expect(callCount).toBe(2)
  })
})
