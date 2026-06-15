import { describe, expect, it, vi } from 'vitest'
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
  it('does not show Duxin in the sidebar', async () => {
    const wrapper = mount(BasicLayout, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: {
                token: 'test-token'
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

    expect(wrapper.find('[data-test="nav-duxin"]').exists()).toBe(false)
  })
})
