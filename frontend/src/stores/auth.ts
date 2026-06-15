import { defineStore } from 'pinia'
import request, { clearRequestCache } from '@/utils/request'
import { message } from 'ant-design-vue'
import {
  clearAuthSession,
  getStoredUser,
  normalizeAuthTokenPayload,
  readAuthSession,
  saveAuthSession,
  setAuthUser,
  type AuthTokenPayload,
} from '@/utils/auth-session'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useGodStore } from '@/stores/god'
import { useAgentStore } from '@/stores/agent'

interface User {
  id: number
  username: string
  role: string
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  accessTokenExpiresAt: string | null
  refreshTokenExpiresAt: string | null
  loading: boolean
  error: string | null
}

const loadInitialState = (): Omit<AuthState, 'loading' | 'error'> => {
  const session = readAuthSession()
  return {
    token: session.token,
    refreshToken: session.refreshToken,
    user: session.user,
    accessTokenExpiresAt: session.accessTokenExpiresAt,
    refreshTokenExpiresAt: session.refreshTokenExpiresAt,
  }
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    ...loadInitialState(),
    loading: false,
    error: null,
  }),
  actions: {
    syncSessionFromStorage() {
      const session = readAuthSession()
      this.token = session.token
      this.refreshToken = session.refreshToken
      this.user = session.user
      this.accessTokenExpiresAt = session.accessTokenExpiresAt
      this.refreshTokenExpiresAt = session.refreshTokenExpiresAt
    },

    clearSession() {
      this.token = null
      this.refreshToken = null
      this.user = null
      this.accessTokenExpiresAt = null
      this.refreshTokenExpiresAt = null
      this.error = null
      clearAuthSession()
    },

    applySession(payload: AuthTokenPayload, user?: User | null) {
      const normalized = normalizeAuthTokenPayload(payload)
      saveAuthSession(normalized, user ?? this.user)
      this.token = normalized.access_token
      this.refreshToken = normalized.refresh_token
      this.accessTokenExpiresAt = normalized.access_token_expires_at
      this.refreshTokenExpiresAt = normalized.refresh_token_expires_at

      if (user !== undefined) {
        this.user = user
      } else {
        this.user = getStoredUser()
      }
    },

    async login(form: Record<string, string>) {
      this.loading = true
      this.error = null
      try {
        const formData = new FormData()
        formData.append('username', form.username)
        formData.append('password', form.password)

        const res = await request.post('/auth/login', formData)
        this.applySession(res.data)

        const userRes = await request.get('/users/me')
        this.user = userRes.data
        setAuthUser(this.user)

        message.success('登录成功')
        const router = (await import('@/router')).default
        router.push('/')
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
          const error = err as any
          this.error = error.response?.data?.detail || '登录失败，请检查用户名或密码'
        } else {
          this.error = '登录失败，请检查用户名或密码'
        }
      } finally {
        this.loading = false
      }
    },

    async register(form: Record<string, string>) {
      this.loading = true
      this.error = null
      try {
        await request.post('/auth/register', {
          username: form.username,
          password: form.password,
        })
        message.success('注册成功，正在自动登录...')
        await this.login(form)
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
          const error = err as any
          this.error = error.response?.data?.detail || '注册失败，请稍后重试'
        } else {
          this.error = '注册失败，请稍后重试'
        }
      } finally {
        this.loading = false
      }
    },

    async logout() {
      this.clearSession()
      clearRequestCache()

      const forumStore = useForumStore()
      forumStore.disconnectWebSocket()
      forumStore.clearForumData()
      forumStore.forums = []
      forumStore.moderators = []
      forumStore.systemLogs = []
      forumStore.loading = false
      forumStore.thinking = false

      const personaStore = usePersonaStore()
      personaStore.personas = []
      personaStore.loading = false

      const godStore = useGodStore()
      godStore.clearHistory()

      const agentStore = useAgentStore()
      agentStore.reset()

      const router = (await import('@/router')).default
      router.push('/auth/login')
      message.success('已退出登录')
    },
  },
})
