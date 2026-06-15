const { request } = require('../../utils/request')
const auth = require('../../utils/auth')

const examples = [
  {
    label: '商业分析型',
    prompt: '生成一个擅长商业分析、市场判断和决策支持的智能体，最好有数据分析背景。',
  },
  {
    label: '写作策划型',
    prompt: '生成一个擅长内容策划、文案创作和选题洞察的智能体，适合辅助内容生产。',
  },
  {
    label: '技术顾问型',
    prompt: '生成一个擅长技术架构、产品实现和方案评审的智能体，要求逻辑清晰。',
  },
  {
    label: '情绪陪伴型',
    prompt: '生成一个温和、耐心、擅长安抚和陪伴用户的智能体。',
  },
]

const nowIso = () => new Date().toISOString()

const normalizeText = (value) => String(value || '').trim()

const stringifyDetail = (value) => {
  if (typeof value === 'string') return value.trim()
  if (value == null) return ''
  try {
    return JSON.stringify(value)
  } catch (error) {
    return String(value)
  }
}

const normalizeTheories = (value) => {
  if (Array.isArray(value)) return value.map((item) => normalizeText(item)).filter(Boolean)
  if (typeof value === 'string') {
    return value.split(/[,，]/).map((item) => item.trim()).filter(Boolean)
  }
  return []
}

const parseSseText = (text) => {
  const events = []
  String(text || '')
    .split('\n\n')
    .forEach((block) => {
      const line = block.trim()
      if (!line.startsWith('data: ')) return
      const payloadText = line.slice(6).trim()
      if (!payloadText || payloadText === '[DONE]') return
      try {
        events.push(JSON.parse(payloadText))
      } catch (error) {
        events.push({ type: 'text', content: payloadText })
      }
    })
  return events
}

const uniquePersonas = (list, nextItem) => {
  const normalized = {
    ...nextItem,
    theories: normalizeTheories(nextItem.theories),
  }
  const key = `${normalizeText(normalized.name).toLowerCase()}::${normalizeText(normalized.system_prompt).toLowerCase()}`
  if (!key || key === '::') return list

  const index = list.findIndex((item) => {
    const itemKey = `${normalizeText(item.name).toLowerCase()}::${normalizeText(item.system_prompt).toLowerCase()}`
    return itemKey === key
  })

  if (index >= 0) {
    const next = list.slice()
    next[index] = Object.assign({}, next[index], normalized)
    return next
  }

  return list.concat([normalized])
}

Page({
  data: {
    draft: '',
    loading: false,
    statusText: '',
    plannedCount: 0,
    currentCount: 0,
    generatedPersonas: [],
    conversation: [
      {
        id: 'welcome',
        role: 'assistant',
        content: '我是女娲智能体。你可以直接描述你想要的智能体画像，我会为你生成并自动保存到智能体工坊。',
        created_at: nowIso(),
      },
    ],
    examples,
    scrollIntoView: 'welcome',
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }
  },

  onDraftInput(e) {
    this.setData({ draft: e.detail.value })
  },

  useExample(e) {
    const prompt = normalizeText(e.currentTarget.dataset.prompt)
    if (!prompt) return
    this.setData({ draft: prompt })
  },

  clearDraft() {
    this.setData({ draft: '' })
  },

  goPersonas() {
    wx.switchTab({ url: '/pages/personas/index' })
  },

  async generate() {
    const prompt = normalizeText(this.data.draft)
    if (!prompt || this.data.loading) return

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      created_at: nowIso(),
    }
    const assistantMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '女娲正在解析你的需求并生成智能体...',
      created_at: nowIso(),
    }
    const conversation = this.data.conversation.concat([userMessage, assistantMessage])

    this.setData({
      draft: '',
      loading: true,
      statusText: '女娲正在生成智能体，请稍候...',
      plannedCount: 0,
      currentCount: 0,
      generatedPersonas: [],
      conversation,
      scrollIntoView: assistantMessage.id,
    })

    try {
      const response = await request({
        url: '/god/generate_real',
        method: 'POST',
        data: {
          prompt,
          n: 1,
        },
        header: { 'content-type': 'application/json' },
        timeout: 300000,
      })

      const events = parseSseText(response.data)
      const nextConversation = conversation.slice()
      const assistantIndex = nextConversation.findIndex((item) => item.id === assistantMessage.id)
      let nextStatus = '智能体生成完成。'
      let plannedCount = this.data.plannedCount
      let currentCount = this.data.currentCount
      let generatedPersonas = this.data.generatedPersonas.slice()

      events.forEach((event) => {
        const eventType = event.type || 'text'
        const content = event.content

        if (eventType === 'count') {
          const value = Number(content)
          if (!Number.isNaN(value) && value > 0) {
            plannedCount = value
          }
        } else if (eventType === 'progress') {
          const current = Number(event.current)
          const total = Number(event.total)
          if (!Number.isNaN(current) && current > 0) {
            currentCount = current
          }
          if (!Number.isNaN(total) && total > 0) {
            plannedCount = total
          }
          nextStatus = `正在生成第 ${event.current ?? '?'} 位智能体${event.total ? ` / 共 ${event.total} 位` : ''}`
        } else if (eventType === 'status') {
          nextStatus = typeof content === 'string' && content.trim()
            ? content.trim()
            : nextStatus
        } else if (eventType === 'thought_start') {
          nextStatus = '女娲已进入生成流程，正在构建智能体。'
        } else if (eventType === 'result') {
          const results = Array.isArray(content) ? content : content ? [content] : []
          results.forEach((item) => {
            if (item && typeof item === 'object') {
              generatedPersonas = uniquePersonas(generatedPersonas, item)
            }
          })
        } else if (eventType === 'error') {
          nextStatus = stringifyDetail(content) || '生成失败'
          if (assistantIndex >= 0) {
            nextConversation[assistantIndex].content = nextStatus
          }
        }
      })

      if (assistantIndex >= 0 && generatedPersonas.length > 0) {
        nextConversation[assistantIndex].content = `生成完成，共保存 ${generatedPersonas.length} 个智能体。`
      } else if (assistantIndex >= 0 && !normalizeText(nextConversation[assistantIndex].content)) {
        nextConversation[assistantIndex].content = nextStatus
      }

      this.setData({
        conversation: nextConversation,
        statusText: generatedPersonas.length > 0 ? `已生成 ${generatedPersonas.length} 个智能体，已自动保存到工坊。` : nextStatus,
        plannedCount,
        currentCount,
        generatedPersonas,
        scrollIntoView: nextConversation[nextConversation.length - 1]?.id || this.data.scrollIntoView,
      })

      wx.showToast({
        title: generatedPersonas.length > 0 ? '生成完成' : '已完成',
        icon: 'success',
      })
    } catch (error) {
      const responseDetail = error && error.data && error.data.detail
        ? error.data.detail
        : typeof (error && error.data) === 'string' && error.data.trim()
          ? error.data.trim()
          : ''
      const detail = responseDetail
        || stringifyDetail(error && (error.errMsg || error.message))
        || (error && typeof error.statusCode === 'number' ? `HTTP ${error.statusCode}` : '')
        || '生成失败'
      const nextConversation = conversation.slice()
      const assistantIndex = nextConversation.findIndex((item) => item.id === assistantMessage.id)
      if (assistantIndex >= 0) {
        nextConversation[assistantIndex].content = detail
      }
      this.setData({
        conversation: nextConversation,
        statusText: detail,
      })
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})
