import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import ChatBubble from '../ChatBubble.vue'
import ParticipantList from '../ParticipantList.vue'

describe('forum avatar rendering', () => {
  it('renders participant image avatars when persona.avatar is available', () => {
    const wrapper = mount(ParticipantList, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              forum: {
                currentForum: {
                  participants: [
                    {
                      persona: {
                        id: 1,
                        name: '洞察者',
                        title: '策略顾问',
                        stance: '支持',
                        bio: '关注长期价值。',
                        avatar: '/uploads/avatars/insight.png'
                      }
                    }
                  ]
                }
              }
            }
          })
        ],
        stubs: {
          'a-avatar': { template: '<div class="avatar"><slot /></div>' },
          'a-tag': { template: '<span><slot /></span>' },
          'a-tooltip': { template: '<span><slot /></span>' }
        }
      }
    })

    const avatar = wrapper.find('.avatar img')
    expect(avatar.exists()).toBe(true)
    expect(avatar.attributes('src')).toBe('/uploads/avatars/insight.png')
  })

  it('renders chat bubble image avatars when avatar prop is available', () => {
    const wrapper = mount(ChatBubble, {
      props: {
        speakerName: '洞察者',
        content: '我认为这个方案值得继续推进。',
        timestamp: new Date().toISOString(),
        isSelf: false,
        avatar: 'data:image/svg+xml;charset=UTF-8,%3Csvg%3E%3C/svg%3E'
      },
      global: {
        stubs: {
          'a-avatar': { template: '<div class="avatar"><slot /><slot name="icon" /></div>' },
          'a-tag': { template: '<span><slot /></span>' },
          'a-collapse': { template: '<div><slot /></div>' },
          'a-collapse-panel': { template: '<div><slot /></div>' },
          UserOutlined: true,
          LoadingOutlined: true,
          BulbOutlined: true
        }
      }
    })

    const avatar = wrapper.find('.avatar img')
    expect(avatar.exists()).toBe(true)
    expect(avatar.attributes('src')).toBe('data:image/svg+xml;charset=UTF-8,%3Csvg%3E%3C/svg%3E')
  })
})
