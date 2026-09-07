import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import Antd from 'ant-design-vue'
import BasicLayout from '../BasicLayout.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({
    path: '/time-gate'
  }),
  useRouter: () => ({
    push: vi.fn()
  })
}))

describe('BasicLayout navigation', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  const mountLayout = () => mount(BasicLayout, {
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            auth: {
              token: 'test-token',
              user: {
                id: 42,
                username: '13555822359',
                role: 'user'
              }
            }
          }
        }),
        Antd
      ],
      stubs: {
        RouterView: true
      }
    }
  })

  it('does not show Duxin in the sidebar', async () => {
    const wrapper = mountLayout()

    expect(wrapper.find('[data-test="nav-duxin"]').exists()).toBe(false)
  })

  it('does not show a separate forum entry in the sidebar', async () => {
    const wrapper = mountLayout()

    expect(wrapper.text()).not.toContain('圆桌论坛')
  })

  it('labels the dashboard entry as home', async () => {
    const wrapper = mountLayout()

    expect(wrapper.text()).toContain('首页')
    expect(wrapper.text()).not.toContain('概览')
  })

  it('shows the signed-in user as a bottom profile entry', async () => {
    const wrapper = mountLayout()

    const profileButton = wrapper.find('[data-test="sidebar-profile"]')
    expect(profileButton.exists()).toBe(true)
    expect(profileButton.find('img').exists()).toBe(false)
    expect(profileButton.text()).toContain('13555822359')
    expect(profileButton.text()).toContain('ID 42')
    expect(wrapper.find('[data-test="nav-logout"]').exists()).toBe(false)
  })

  it('does not expose an avatar picker in the profile popover', async () => {
    const wrapper = mountLayout()

    await wrapper.find('[data-test="sidebar-profile"]').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 250))

    expect(document.body.textContent).not.toContain('头像形象')
    expect(document.body.querySelector('[data-test="profile-avatar-picker"]')).toBeNull()
  })
})
