import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useGodStore } from '@/stores/god'
import { useAgentStore } from '@/stores/agent'

const { pushMock, clearCacheMock, requestMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  clearCacheMock: vi.fn(),
  requestMock: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

vi.mock('@/router', () => ({
  default: {
    push: pushMock
  }
}))

vi.mock('@/utils/request', () => ({
  default: requestMock,
  clearRequestCache: clearCacheMock
}))

vi.mock('ant-design-vue', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('Auth store logout', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    pushMock.mockClear()
    clearCacheMock.mockClear()
    requestMock.post.mockClear()
    requestMock.get.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('clears local auth state and request cache on logout', async () => {
    localStorage.setItem('token', 'token-123')
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'alice', role: 'user' }))

    const authStore = useAuthStore()
    const forumStore = useForumStore()
    const personaStore = usePersonaStore()
    const godStore = useGodStore()
    const agentStore = useAgentStore()

    authStore.token = 'token-123'
    authStore.user = { id: 1, username: 'alice', role: 'user' }
    forumStore.forums = [{ id: 1, topic: 'Forum', creator_id: 1, status: 'running', start_time: '', summary_history: [] } as any]
    forumStore.currentForum = { id: 1, topic: 'Forum', creator_id: 1, status: 'running', start_time: '', summary_history: [] } as any
    forumStore.messages = [{ id: 1, forum_id: 1, persona_id: 1, speaker_name: 'A', content: 'hello', timestamp: 'now' } as any]
    forumStore.systemLogs = [{ timestamp: 'now', level: 'info', content: 'log' }]
    forumStore.isConnected = true
    personaStore.personas = [{ id: 1, owner_id: 1, name: 'P', title: '', bio: '', theories: [], stance: '', system_prompt: '', is_public: false }]
    godStore.messages = [{ role: 'user', content: 'prompt', timestamp: Date.now() }]
    agentStore.context = [{ speaker: 'User', content: 'hello' }]

    await authStore.logout()

    expect(authStore.token).toBeNull()
    expect(authStore.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
    expect(clearCacheMock).toHaveBeenCalledTimes(1)
    expect(pushMock).toHaveBeenCalledWith('/auth/login')
    expect(forumStore.currentForum).toBeNull()
    expect(forumStore.messages).toEqual([])
    expect(forumStore.systemLogs).toEqual([])
    expect(forumStore.forums).toEqual([])
    expect(forumStore.isConnected).toBe(false)
    expect(personaStore.personas).toEqual([])
    expect(godStore.messages).toEqual([])
    expect(agentStore.context).toEqual([])
  })
})
