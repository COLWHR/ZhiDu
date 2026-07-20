import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import AssistantView from '../AssistantView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn()
  })
}))

describe('AssistantView', () => {
  it('renders an interactive assistant repository header without the gift emoji', async () => {
    const wrapper = mount(AssistantView, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })]
      }
    })

    expect(wrapper.text()).toContain('助手仓库')
    expect(wrapper.text()).toContain('全部助手')
    expect(wrapper.text()).toContain('热门分类')
    expect(wrapper.text()).toContain('当前结果')
    expect(wrapper.text()).toContain('快速添加')
    expect(wrapper.text()).toContain('推荐助手')
    expect(wrapper.find('.greeting-emoji').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('🎁')

    const topCategoryButton = wrapper
      .findAll('button')
      .find(button => button.text().includes('热门分类'))

    expect(topCategoryButton).toBeTruthy()
    await topCategoryButton!.trigger('click')

    expect((wrapper.vm as any).currentCategory).toBe((wrapper.vm as any).topCategory.name)
  })
})
