import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import DuxinView from '../DuxinView.vue'

const stubs = {
  'a-alert': { template: '<div class="alert"><slot />{{ message }}{{ description }}</div>', props: ['message', 'description'] },
  'a-avatar': { template: '<div class="avatar"><slot /></div>' },
  'a-button': { template: '<button class="ant-btn" @click="$emit(\'click\')"><slot /></button>' },
  'a-empty': { template: '<div class="empty">{{ description }}</div>', props: ['description'] },
  'a-spin': { template: '<div class="spin" />' },
  'a-tag': { template: '<span class="tag"><slot /></span>' },
  'a-textarea': { template: '<textarea />' },
  InboxOutlined: true,
  ReloadOutlined: true,
  SendOutlined: true,
  TeamOutlined: true,
  UserSwitchOutlined: true
}

describe('DuxinView', () => {
  it('renders a simple intake-first flow', () => {
    const wrapper = mount(DuxinView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: { user: { id: 1, username: 'test_user' } },
              duxin: {
                sessions: [],
                currentSession: null,
                messages: [],
                teamPlan: null,
                loading: false,
                streaming: false,
                composerStatus: '',
                riskLevel: 'L0'
              }
            }
          })
        ],
        stubs
      }
    })

    expect(wrapper.text()).toContain('先和智小渡说说你现在的状态')
    expect(wrapper.text()).toContain('倾诉')
    expect(wrapper.text()).toContain('判断')
    expect(wrapper.text()).toContain('分配')
    expect(wrapper.text()).toContain('你希望我现在怎么陪你？')
    expect(wrapper.text()).toContain('只陪我一会儿')
    expect(wrapper.text()).toContain('帮我理清楚')
    expect(wrapper.text()).toContain('给我一个小行动')
    expect(wrapper.text()).toContain('我现在很危险')
    expect(wrapper.text()).not.toContain('保存记忆')
    expect(wrapper.text()).not.toContain('提交反馈')
  })

  it('offers a heart-light card and real-world support message after a conversation', () => {
    const wrapper = mount(DuxinView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: { user: { id: 1, username: 'test_user' } },
              duxin: {
                sessions: [],
                currentSession: { id: 1, user_id: 1, title: '想找人陪一下', mode: 'support', risk_level: 'L1', status: 'active', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
                messages: [
                  {
                    id: 1,
                    session_id: 1,
                    user_id: 1,
                    role: 'assistant',
                    agent_name: '智小渡',
                    content: '你已经很努力地撑到现在了。我们先不急着解决全部，只先照顾这一分钟。',
                    risk_level: 'L1',
                    metadata: {},
                    created_at: new Date().toISOString()
                  }
                ],
                teamPlan: null,
                loading: false,
                streaming: false,
                composerStatus: '',
                riskLevel: 'L1'
              }
            }
          })
        ],
        stubs
      }
    })

    expect(wrapper.text()).toContain('心灯卡')
    expect(wrapper.text()).toContain('你不是一个需要立刻被修好的人')
    expect(wrapper.text()).toContain('现实求助短信')
    expect(wrapper.text()).toContain('我现在状态不太好，不需要你解决问题')
  })

  it('shows the counselor assigned by Zhixiaodu from the team plan', () => {
    const wrapper = mount(DuxinView, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: { user: { id: 1, username: 'test_user' } },
              duxin: {
                sessions: [],
                currentSession: { id: 1, user_id: 1, title: '最近压力很大', mode: 'support', risk_level: 'L1', status: 'active', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
                messages: [],
                teamPlan: {
                  mode: 'support',
                  primary_agent: { key: 'zhidu', name: '智小渡', role: '总协调', style: '温和', focus: '先接住情绪' },
                  members: [
                    { key: 'zhidu', name: '智小渡', role: '总协调', style: '温和', focus: '先接住情绪' },
                    { key: 'stabilizer', name: '情绪安抚员', role: '心理咨询师', style: '低刺激', focus: '先稳定身体和情绪' }
                  ],
                  handoff_reason: '用户呈现明显压力，先安排情绪稳定支持。',
                  summary: '压力支持'
                },
                loading: false,
                streaming: false,
                composerStatus: '',
                riskLevel: 'L1'
              }
            }
          })
        ],
        stubs
      }
    })

    expect(wrapper.text()).toContain('智小渡建议先见')
    expect(wrapper.text()).toContain('情绪安抚员')
    expect(wrapper.text()).toContain('用户呈现明显压力')
  })
})
