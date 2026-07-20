import { describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Antd from 'ant-design-vue'
import SkillRepositoryView from '../SkillRepositoryView.vue'

const requestMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn()
}))

vi.mock('@/utils/request', () => ({
  default: requestMock
}))

describe('SkillRepositoryView', () => {
  it('renders SkillHub skills from the global catalog', async () => {
    setActivePinia(createPinia())
    requestMock.get.mockResolvedValueOnce({
      data: [
        {
          skill_key: 'skillhub.web-tools-guide',
          name: 'web-tools-guide',
          category: 'knowledge-management',
          description: '联网检索工具指南',
          input_modalities: ['text'],
          output_types: ['text'],
          required_models: ['fast'],
          required_tools: [],
          params_schema: {},
          permission_scope: ['skillhub'],
          cost_level: 'low',
          status: 'active',
          source: 'skillhub',
          source_url: 'https://www.skillhub.cn/skills/web-tools-guide',
          source_rank: 1,
          downloads: 100,
          installs: 20,
          stars: 5,
          sub_categories: ['信息检索']
        }
      ]
    })

    const wrapper = mount(SkillRepositoryView, {
      global: {
        plugins: [Antd]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Skill 仓库')
    expect(wrapper.text()).toContain('web-tools-guide')
    expect(wrapper.text()).toContain('联网检索工具指南')
    expect(wrapper.text()).toContain('知识管理')
    expect(wrapper.text()).toContain('查看详情')
    expect(wrapper.text()).not.toContain('knowledge-management')
    expect(wrapper.text()).not.toContain('全部来源')
    expect(wrapper.text()).not.toContain('内置')

    expect(wrapper.html().indexOf('page-band')).toBeLessThan(wrapper.html().indexOf('stats-row'))

    const detailButton = wrapper
      .findAll('button')
      .find(button => button.text().includes('查看详情'))

    expect(detailButton).toBeTruthy()
    await detailButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Skill Key')
    expect(wrapper.text()).toContain('skillhub.web-tools-guide')
    expect(wrapper.text()).toContain('成本等级')
    expect(wrapper.text()).toContain('低')
    expect(wrapper.text()).toContain('能力信息')
    expect(wrapper.text()).toContain('输入')
    expect(wrapper.text()).toContain('文本')
    expect(wrapper.text()).toContain('输出')
    expect(wrapper.text()).toContain('权限')
    expect(wrapper.text()).toContain('来源与标签')
    expect(wrapper.text()).toContain('https://www.skillhub.cn/skills/web-tools-guide')
  })
})
