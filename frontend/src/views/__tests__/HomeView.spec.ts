import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import HomeView from '../HomeView.vue'
import { createTestingPinia } from '@pinia/testing'
import { createI18n } from 'vue-i18n'
import Antd from 'ant-design-vue'

const i18n = createI18n({
  locale: 'en',
  legacy: false,
  messages: {
    en: {
      agent: {
        title: 'Agent Chat',
        inputPlaceholder: 'Enter...',
        send: 'Send',
        thinking: 'Thinking...',
        clear: 'Clear',
        history: 'History'
      }
    }
  }
})

describe('HomeView', () => {
  it('renders properly', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [
          createTestingPinia({ createSpy: vi.fn }),
          i18n,
          Antd
        ],
        stubs: {
          'router-link': true
        }
      }
    })
    expect(wrapper.text()).toContain('7日活跃')
    expect(wrapper.text()).toContain('圆桌论坛')
    expect(wrapper.text()).toContain('发起新论坛')
    expect(wrapper.text()).toContain('新建智能体')
    expect(wrapper.text()).not.toContain('圆桌脉冲')
    expect(wrapper.text()).not.toContain('论坛总数')
    expect(wrapper.text()).not.toContain('快捷操作')
    expect(wrapper.text()).not.toContain('我的智能体')
    expect(wrapper.find('.stats-row').exists()).toBe(false)
    expect(wrapper.find('.stat-card').exists()).toBe(false)
  })

  it('opens the forum creation modal from overview instead of navigating to the forum list', async () => {
    const push = vi.fn()
    const wrapper = mount(HomeView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              forum: {
                forums: [],
                moderators: [],
                loading: false
              },
              persona: {
                personas: [
                  {
                    id: 1,
                    name: 'Alpha'
                  }
                ],
                loading: false
              },
              auth: {
                user: {
                  id: 1,
                  username: 'tester'
                }
              }
            }
          }),
          i18n,
          Antd
        ],
        mocks: {
          $router: { push }
        },
        stubs: {
          'router-link': true
        }
      }
    })

    const createButtons = wrapper.findAll('button').filter(button => button.text().includes('发起'))
    expect(createButtons.length).toBeGreaterThan(0)

    await createButtons[0].trigger('click')
    await wrapper.vm.$nextTick()

    expect(push).not.toHaveBeenCalledWith('/forums')
    expect((wrapper.vm as any).createModalVisible).toBe(true)

    const personaButton = wrapper.findAll('button').find(button => button.text().includes('新建智能体'))
    expect(personaButton).toBeTruthy()

    await personaButton!.trigger('click')
    expect(push).toHaveBeenCalledWith('/personas')
  })

  it('renders interactive dashboard visualization sections', () => {
    const wrapper = mount(HomeView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              forum: {
                forums: [
                  {
                    id: 1,
                    topic: 'Future Work',
                    status: 'running',
                    start_time: new Date().toISOString(),
                    summary_history: []
                  }
                ],
                loading: false
              },
              persona: {
                personas: [
                  {
                    id: 1,
                    name: 'Alpha'
                  }
                ],
                loading: false
              },
              auth: {
                user: {
                  id: 1,
                  username: 'tester'
                }
              }
            }
          }),
          i18n,
          Antd
        ],
        stubs: {
          'router-link': true
        }
      }
    })

    expect(wrapper.text()).toContain('7日活跃')
    expect(wrapper.text()).toContain('智能体星图')
    expect(wrapper.text()).toContain('议题发射台')
    expect(wrapper.text()).toContain('模拟一次发布前的红队评审')
    expect(wrapper.text()).toContain('把一个模糊需求拆成三条可执行路线')
    expect(wrapper.text()).not.toContain('圆桌脉冲')
  })
})
