const systemAgents = require('../../data/system-agents')
const { request } = require('../../utils/request')
const auth = require('../../utils/auth')

const nowIso = () => new Date().toISOString()
const normalizeText = (value) => String(value || '').trim()

const agentSpeaker = (agent) => normalizeText(agent && agent.name) || '智能体'

const toPersonaPayload = (agent) => ({
  name: normalizeText(agent.name),
  title: normalizeText(agent.title) || normalizeText(agent.description) || '智能体',
  bio: normalizeText(agent.description),
  stance: normalizeText(agent.title) || normalizeText(agent.description),
  system_prompt: normalizeText(agent.prompt),
  theories: Array.isArray(agent.group) ? agent.group : [],
  is_public: false,
})

const welcomeMessage = (agent) => ({
  id: `welcome-${agent.id}`,
  role: 'assistant',
  speaker: agentSpeaker(agent),
  content: `你好，我是${agentSpeaker(agent)}。${normalizeText(agent.description) || '我可以基于自己的设定和你直接对话。'}`,
  created_at: nowIso(),
})

const buildCategories = (agents) => {
  const categories = ['全部']
  const seen = new Set()
  agents.forEach((agent) => {
    ;(agent.group || []).forEach((group) => {
      if (!seen.has(group)) {
        seen.add(group)
        categories.push(group)
      }
    })
  })
  return categories
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
        events.push({ type: 'chunk', content: payloadText })
      }
    })
  return events
}

const buildPersonaKey = (agent) => {
  const name = normalizeText(agent && agent.name).toLowerCase()
  const prompt = normalizeText(agent && agent.prompt).toLowerCase()
  return `${name}::${prompt}`
}

const findAgentById = (agents, id) => {
  const target = String(id)
  return (Array.isArray(agents) ? agents : []).find((item) => String(item.id) === target)
}

Page({
  data: {
    categories: ['全部'],
    currentCategory: '全部',
    searchText: '',
    agents: [],
    filteredAgents: [],
    selectedAgent: null,
    importing: false,
    showDetail: false,
    showChat: false,
    chatAgentId: 0,
    chatMessages: [],
    chatInput: '',
    chatSending: false,
    chatScrollIntoView: '',
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }

    const agents = Array.isArray(systemAgents) ? systemAgents : []
    this.setData(
      {
        categories: buildCategories(agents),
        agents,
      },
      () => this.updateFilteredAgents(),
    )
  },

  updateFilteredAgents() {
    const keyword = normalizeText(this.data.searchText).toLowerCase()
    let agents = this.data.agents || []

    if (this.data.currentCategory !== '全部') {
      agents = agents.filter((item) => Array.isArray(item.group) && item.group.includes(this.data.currentCategory))
    }

    if (keyword) {
      agents = agents.filter((item) =>
        [item.name, item.title, item.description, item.prompt, ...(item.group || [])]
          .join(' ')
          .toLowerCase()
          .includes(keyword),
      )
    }

    this.setData({ filteredAgents: agents })
  },

  onCategoryTap(e) {
    this.setData({ currentCategory: e.currentTarget.dataset.name }, () => this.updateFilteredAgents())
  },

  onSearchInput(e) {
    this.setData({ searchText: e.detail.value }, () => this.updateFilteredAgents())
  },

  openDetail(e) {
    const id = e.currentTarget.dataset.id
    const agent = findAgentById(this.data.agents, id)
    if (!agent) return
    this.setData({ selectedAgent: agent, showDetail: true, showChat: false })
  },

  openChat(e) {
    const id = e.currentTarget.dataset.id
    const agent = findAgentById(this.data.agents, id)
    if (!agent) return

    const chatMessages = String(this.data.chatAgentId) === String(agent.id) && this.data.chatMessages.length
      ? this.data.chatMessages
      : [welcomeMessage(agent)]

    this.setData({
      selectedAgent: agent,
      showDetail: false,
      showChat: true,
      chatAgentId: agent.id,
      chatMessages,
      chatInput: '',
      chatScrollIntoView: chatMessages.length ? chatMessages[chatMessages.length - 1].id : '',
    })
  },

  closeDetail() {
    this.setData({ showDetail: false })
  },

  closeChat() {
    this.setData({ showChat: false, chatSending: false })
  },

  syncChatScroll() {
    const last = this.data.chatMessages[this.data.chatMessages.length - 1]
    if (!last) return
    this.setData({ chatScrollIntoView: last.id })
  },

  onChatInput(e) {
    this.setData({ chatInput: e.detail.value })
  },

  async getExistingPersonaKeys() {
    const res = await request({
      url: '/personas/',
      method: 'GET',
    })
    const personas = Array.isArray(res.data) ? res.data : []
    return new Set(personas.map((persona) => buildPersonaKey(persona)).filter((key) => key !== '::'))
  },

  async createPersonaFromAgent(agent) {
    return request({
      url: '/personas/',
      method: 'POST',
      data: toPersonaPayload(agent),
      header: { 'content-type': 'application/json' },
    })
  },

  async importAgentToWorkshop(agent, options = {}) {
    if (!agent) return false

    const existingKeys = options.existingKeys || (await this.getExistingPersonaKeys())
    const key = buildPersonaKey(agent)
    if (existingKeys.has(key)) {
      wx.showToast({ title: '已存在', icon: 'none' })
      return false
    }

    this.setData({ importing: true })
    try {
      await this.createPersonaFromAgent(agent)
      existingKeys.add(key)
      wx.showToast({ title: '导入成功', icon: 'success' })

      if (options.navigateAfterImport) {
        this.closeDetail()
        this.setData({ showChat: false })
        wx.switchTab({ url: '/pages/personas/index' })
      }

      return true
    } catch (error) {
      const detail = error && error.data && error.data.detail ? error.data.detail : '导入失败'
      wx.showToast({ title: detail, icon: 'none' })
      return false
    } finally {
      this.setData({ importing: false })
    }
  },

  async importAgentFromCard(e) {
    const id = e.currentTarget.dataset.id
    const agent = findAgentById(this.data.agents, id)
    if (!agent) return
    await this.importAgentToWorkshop(agent, { navigateAfterImport: false })
  },

  async importFilteredAgents() {
    const agents = this.data.filteredAgents || []
    if (!agents.length) {
      wx.showToast({ title: '没有可导入的助手', icon: 'none' })
      return
    }

    this.setData({ importing: true })
    try {
      const existingKeys = await this.getExistingPersonaKeys()
      let importedCount = 0
      let skippedCount = 0

      for (const agent of agents) {
        const key = buildPersonaKey(agent)
        if (existingKeys.has(key)) {
          skippedCount += 1
          continue
        }

        await this.createPersonaFromAgent(agent)
        existingKeys.add(key)
        importedCount += 1
      }

      if (importedCount === 0 && skippedCount > 0) {
        wx.showToast({ title: '全部已存在', icon: 'none' })
      } else {
        wx.showToast({ title: '导入完成', icon: 'success' })
      }
      wx.switchTab({ url: '/pages/personas/index' })
    } catch (error) {
      const detail = error && error.data && error.data.detail ? error.data.detail : '导入失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ importing: false })
    }
  },

  async importSelectedAgent() {
    if (!this.data.selectedAgent) return
    await this.importAgentToWorkshop(this.data.selectedAgent, { navigateAfterImport: true })
  },

  async sendChat() {
    const text = normalizeText(this.data.chatInput)
    if (!text || this.data.chatSending || !this.data.selectedAgent) return

    const agent = this.data.selectedAgent
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      speaker: '用户',
      content: text,
      created_at: nowIso(),
    }
    const assistantMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      speaker: agentSpeaker(agent),
      content: '',
      created_at: nowIso(),
    }

    const conversationMessages = this.data.chatMessages.concat([userMessage])
    const pendingMessages = conversationMessages.concat([assistantMessage])

    this.setData({
      chatInput: '',
      chatMessages: pendingMessages,
      chatSending: true,
      chatScrollIntoView: assistantMessage.id,
    })

    try {
      const response = await request({
        url: '/agents/chat/stream',
        method: 'POST',
        data: {
          agent_name: agentSpeaker(agent),
          persona_json: agent,
          context_messages: conversationMessages,
          theme: normalizeText(agent.title) || normalizeText(agent.description) || '智能体助手',
        },
        header: { 'content-type': 'application/json' },
      })

      const rawResponse = typeof response.data === 'string'
        ? response.data
        : JSON.stringify(response.data || '')
      const events = parseSseText(rawResponse)
      const nextMessages = pendingMessages.slice()
      const assistantIndex = nextMessages.findIndex((item) => item.id === assistantMessage.id)

      if (assistantIndex < 0) {
        throw new Error('未能找到对话占位消息')
      }

      events.forEach((event) => {
        if (typeof event.content === 'string') {
          nextMessages[assistantIndex].content = `${nextMessages[assistantIndex].content || ''}${event.content}`
        }
      })

      if (!nextMessages[assistantIndex].content.trim()) {
        nextMessages[assistantIndex].content = '暂时没有拿到有效回复，请稍后再试。'
      }

      this.setData({
        chatMessages: nextMessages,
      }, () => this.syncChatScroll())
    } catch (error) {
      const message = error && error.data && error.data.detail ? error.data.detail : '智能体暂时无法回复'
      const nextMessages = pendingMessages.slice()
      const assistantIndex = nextMessages.findIndex((item) => item.id === assistantMessage.id)
      if (assistantIndex >= 0) {
        nextMessages[assistantIndex].content = message
        this.setData({
          chatMessages: nextMessages,
        }, () => this.syncChatScroll())
      } else {
        wx.showToast({ title: message, icon: 'none' })
      }
    } finally {
      this.setData({ chatSending: false })
    }
  },

  goPersonas() {
    wx.switchTab({ url: '/pages/personas/index' })
  },

  goForums() {
    wx.switchTab({ url: '/pages/forums/list/index' })
  },

  noop() {},
})
