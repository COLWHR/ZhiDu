import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ForumDetailView from '../ForumDetailView.vue'
import { createTestingPinia } from '@pinia/testing'
import { useRoute, useRouter } from 'vue-router'

const { mockRouter } = vi.hoisted(() => ({
  mockRouter: {
    push: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn(() => mockRouter)
}))

vi.mock('@/composables/useForumWebSocket', () => ({
  useForumWebSocket: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    isConnected: { value: true }
  }))
}))

vi.mock('ant-design-vue', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('ForumDetailView', () => {
  it('renders header buttons correctly', async () => {
    ;(useRoute as any).mockReturnValue({
      params: { id: '1' }
    })

    const wrapper = mount(ForumDetailView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              forum: {
                currentForum: {
                  id: 1,
                  topic: 'Test Forum',
                  status: 'running',
                  start_time: new Date().toISOString(),
                  duration_minutes: 30
                },
                messages: [],
                loading: false
              },
              auth: { user: { id: 1 } },
              persona: { personas: [] }
            }
          })
        ],
        stubs: {
          MessageList: true,
          ForumTimer: true,
          ParticipantList: true,
          SystemLogConsole: true,
          ArrowLeftOutlined: true,
          TeamOutlined: true,
          DeleteOutlined: true,
          PlayCircleOutlined: true,
          CodeOutlined: true,
          UserOutlined: true,
          UploadOutlined: true,
          'a-button': { template: '<button class="ant-btn"><slot /></button>' },
          'a-space': { template: '<div><slot /></div>' },
          'a-tag': { template: '<span><slot /></span>' },
          'a-popconfirm': { template: '<div><slot /></div>' },
          'a-input-search': { template: '<div><slot name="prefix" /><slot /><slot name="suffix" /></div>' },
          'a-upload': { template: '<div><slot /></div>' },
          'a-modal': true
        }
      }
    })

    expect(wrapper.find('.forum-header').exists()).toBe(true)
    expect(wrapper.find('.forum-topic').text()).toBe('Test Forum')

    const backButton = wrapper.find('.header-left button')
    expect(backButton.exists()).toBe(true)

    const rightButtons = wrapper.findAll('.header-right button')
    expect(rightButtons.length).toBe(4)

    await backButton.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
  })
})
