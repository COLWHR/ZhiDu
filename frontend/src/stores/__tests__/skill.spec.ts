import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const requestMock = {
  get: vi.fn(),
  post: vi.fn()
}

vi.mock('@/utils/request', () => ({
  default: requestMock
}))

describe('skill store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    requestMock.get.mockReset()
    requestMock.post.mockReset()
  })

  it('fetches global skill catalog', async () => {
    const { useSkillStore } = await import('../skill')
    requestMock.get.mockResolvedValueOnce({
      data: [
        {
          skill_key: 'skillhub.web-tools-guide',
          name: 'web-tools-guide',
          category: 'knowledge-management',
          source: 'skillhub',
          downloads: 100
        }
      ]
    })

    const store = useSkillStore()
    await store.fetchSkills()

    expect(requestMock.get).toHaveBeenCalledWith('/skills/catalog')
    expect(store.skills).toHaveLength(1)
    expect(store.skillhubSkills[0].skill_key).toBe('skillhub.web-tools-guide')
  })

  it('syncs SkillHub skills and refreshes catalog', async () => {
    const { useSkillStore } = await import('../skill')
    requestMock.post.mockResolvedValueOnce({ data: { count: 1, skills: [] } })
    requestMock.get.mockResolvedValueOnce({ data: [] })

    const store = useSkillStore()
    await store.syncSkillHub(50)

    expect(requestMock.post).toHaveBeenCalledWith('/skills/sync/skillhub', null, { params: { limit: 50 } })
    expect(requestMock.get).toHaveBeenCalledWith('/skills/catalog')
    expect(store.lastSyncCount).toBe(1)
  })
})
