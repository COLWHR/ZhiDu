import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'
import PersonaView from '../PersonaView.vue'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn()
}))

vi.mock('@/utils/request', () => ({
  default: requestMock
}))

describe('PersonaView', () => {
  it('renders the interactive workshop header without emoji decoration', async () => {
    requestMock.get.mockResolvedValueOnce({ data: [] })

    const wrapper = mount(PersonaView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              persona: {
                personas: [
                  {
                    id: 1,
                    owner_id: 1,
                    name: '埃隆·马斯克',
                    title: '科技巨头',
                    bio: 'SpaceX 与 Tesla 创始人。',
                    theories: ['第一性原理'],
                    stance: '追求工程化创新',
                    system_prompt: '',
                    is_public: false,
                    skills: ['chat.reply'],
                    modalities: ['text']
                  },
                  {
                    id: 2,
                    owner_id: 1,
                    name: '扎哈·哈迪德',
                    title: '建筑师',
                    bio: '参数化建筑代表人物。',
                    theories: ['参数化设计'],
                    stance: '突破传统建筑边界',
                    system_prompt: '',
                    is_public: true,
                    skills: ['image.view'],
                    modalities: ['text', 'image']
                  }
                ],
                loading: false
              }
            }
          }),
          Antd
        ],
        stubs: {
          RealGodAgentModal: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('智能体工坊')
    expect(wrapper.text()).toContain('焦点智能体')
    expect(wrapper.text()).toContain('全部智能体')
    expect(wrapper.text()).toContain('公开角色')
    expect(wrapper.text()).toContain('私有角色')
    expect(wrapper.text()).toContain('技能关联')
    expect(wrapper.text()).not.toContain('🤖')

    const publicButton = wrapper
      .findAll('button')
      .find(button => button.text().includes('公开角色'))

    expect(publicButton).toBeTruthy()
    await publicButton!.trigger('click')

    expect(wrapper.text()).toContain('扎哈·哈迪德')
    expect(wrapper.text()).not.toContain('埃隆·马斯克')
  })

  it('offers upload, AI generation, and initial fallback controls for persona avatars', async () => {
    requestMock.get.mockResolvedValueOnce({ data: [] })

    const wrapper = mount(PersonaView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              persona: {
                personas: [],
                loading: false
              }
            }
          }),
          Antd
        ],
        stubs: {
          RealGodAgentModal: true
        }
      }
    })

    await flushPromises()

    const createButton = wrapper
      .findAll('button')
      .find(button => button.text().includes('创建智能体'))

    expect(createButton).toBeTruthy()
    await createButton!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-test="persona-avatar-editor"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="persona-avatar-file"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="persona-avatar-generate"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="persona-avatar-clear"]').exists()).toBe(true)

    await wrapper.find('[data-test="persona-avatar-generate"]').trigger('click')

    expect((wrapper.vm as any).formState.avatar).toMatch(/^data:image\/svg\+xml;charset=UTF-8,/)
  })
})
