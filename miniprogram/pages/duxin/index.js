const { request } = require('../../utils/request')
const auth = require('../../utils/auth')

const nowIso = () => new Date().toISOString()

const modeLabels = {
  support: '情绪支持',
  relationship: '关系梳理',
  growth: '行动整理',
  crisis: '优先稳定',
}

const quickModes = [
  { key: 'support', label: '情绪支持', prompt: '我现在有点乱，先陪我一下。' },
  { key: 'relationship', label: '关系梳理', prompt: '我想把一段关系的情况理清楚。' },
  { key: 'growth', label: '行动整理', prompt: '我想整理问题并找到下一步。' },
  { key: 'crisis', label: '优先稳定', prompt: '我现在很难受，先帮我稳定下来。' },
]

Page({
  data: {
    sessions: [],
    currentSession: null,
    messages: [],
    memories: [],
    memorySummary: null,
    feedbackSummary: null,
    loading: false,
    streaming: false,
    composerStatus: '',
    riskLevel: 'L0',
    riskSummary: '',
    riskSignals: [],
    draft: '',
    mode: 'support',
    currentModeLabel: '情绪支持',
    quickModes,
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }
    this.loadAll()
  },

  async loadAll(autoOpen = true) {
    this.setData({ loading: true })
    try {
      const [sessionsRes, memoriesRes, memorySummaryRes, feedbackSummaryRes] = await Promise.all([
        request({ url: '/duxin/sessions', method: 'GET' }).catch(() => ({ data: [] })),
        request({ url: '/duxin/memories', method: 'GET' }).catch(() => ({ data: [] })),
        request({ url: '/duxin/memories/summary', method: 'GET' }).catch(() => ({ data: null })),
        request({ url: '/duxin/safety/feedback/summary', method: 'GET' }).catch(() => ({ data: null })),
      ])

      const sessions = Array.isArray(sessionsRes.data) ? sessionsRes.data : []
      this.setData({
        sessions,
        memories: Array.isArray(memoriesRes.data) ? memoriesRes.data : [],
        memorySummary: memorySummaryRes.data || null,
        feedbackSummary: feedbackSummaryRes.data || null,
      })

      if (autoOpen && sessions.length > 0 && !this.data.currentSession) {
        await this.openSession(sessions[0].id)
      }
    } catch (error) {
      wx.showToast({ title: '渡心加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  modeLabel(mode) {
    return modeLabels[mode] || '情绪支持'
  },

  selectMode(e) {
    const mode = e.currentTarget.dataset.mode
    this.setData({
      mode,
      currentModeLabel: this.modeLabel(mode),
    })
  },

  applyQuick(e) {
    const key = e.currentTarget.dataset.key
    const found = quickModes.find((item) => item.key === key)
    if (!found) return
    this.setData({
      mode: found.key,
      currentModeLabel: found.label,
      draft: this.data.draft.trim() ? `${this.data.draft.trim()}\n${found.prompt}` : found.prompt,
    })
  },

  onDraftInput(e) {
    this.setData({ draft: e.detail.value })
  },

  async openSession(input) {
    const sessionId = input && input.currentTarget ? input.currentTarget.dataset.id : input
    if (!sessionId) return

    this.setData({ loading: true })
    try {
      const [sessionRes, messagesRes] = await Promise.all([
        request({ url: `/duxin/sessions/${sessionId}`, method: 'GET' }),
        request({ url: `/duxin/sessions/${sessionId}/messages`, method: 'GET' }).catch(() => ({ data: [] })),
      ])

      const currentSession = sessionRes.data
      this.setData({
        currentSession,
        messages: Array.isArray(messagesRes.data) ? messagesRes.data : [],
        mode: currentSession.mode || 'support',
        currentModeLabel: this.modeLabel(currentSession.mode || 'support'),
        riskLevel: currentSession.risk_level || 'L0',
        composerStatus: '',
      })
    } catch (error) {
      wx.showToast({ title: '打开会话失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async ensureSession() {
    if (this.data.currentSession) return this.data.currentSession

    const title = (this.data.draft.trim().slice(0, 18) || '渡心会话')
    const res = await request({
      url: '/duxin/sessions',
      method: 'POST',
      data: {
        mode: this.data.mode,
        title,
      },
      header: { 'content-type': 'application/json' },
    })

    if (!res.data) {
      throw new Error('创建会话失败')
    }

    const session = res.data
    this.setData({
      currentSession: session,
      sessions: [session].concat(this.data.sessions || []),
    })
    return session
  },

  async onSend() {
    const text = String(this.data.draft || '').trim()
    if (!text || this.data.streaming) return

    try {
      const session = await this.ensureSession()
      const userMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        agent_name: '用户',
        content: text,
        created_at: nowIso(),
      }
      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        agent_name: '渡心',
        content: '',
        created_at: nowIso(),
      }

      this.setData({
        draft: '',
        messages: this.data.messages.concat([userMessage, assistantMessage]),
        streaming: true,
        composerStatus: '正在接住你的情绪...',
      })

      const response = await request({
        url: `/duxin/sessions/${session.id}/chat/stream`,
        method: 'POST',
        data: { content: text },
        header: { 'content-type': 'application/json' },
      })

      const parsedEvents = this.parseSseText(response.data)
      const nextMessages = this.data.messages.slice()
      const assistantIndex = nextMessages.findIndex((item) => item.id === assistantMessage.id)

      parsedEvents.forEach((event) => {
        if (event.type === 'session' && event.session) {
          this.setData({ currentSession: event.session })
        } else if (event.type === 'risk') {
          this.setData({
            riskLevel: event.risk_level || this.data.riskLevel,
            riskSummary: typeof event.summary === 'string' ? event.summary : this.data.riskSummary,
            riskSignals: Array.isArray(event.signals) ? event.signals : this.data.riskSignals,
          })
        } else if (event.type === 'agent_status') {
          this.setData({ composerStatus: typeof event.content === 'string' ? event.content : this.data.composerStatus })
        } else if (event.type === 'chunk' && assistantIndex >= 0 && typeof event.content === 'string') {
          nextMessages[assistantIndex].content = `${nextMessages[assistantIndex].content || ''}${event.content}`
        } else if (event.type === 'done') {
          this.setData({ composerStatus: '' })
        } else if (event.type === 'error') {
          const text = typeof event.content === 'string' ? event.content : '渡心回复失败'
          nextMessages[assistantIndex].content = text
        } else if (typeof event.content === 'string' && assistantIndex >= 0) {
          nextMessages[assistantIndex].content = `${nextMessages[assistantIndex].content || ''}${event.content}`
        }
      })

      if (assistantIndex >= 0 && !nextMessages[assistantIndex].content.trim()) {
        nextMessages[assistantIndex].content = '我在。你可以继续说。'
      }

      this.setData({ messages: nextMessages })
      this.loadAll(false)
    } catch (error) {
      const message = error && error.data && error.data.detail ? error.data.detail : '渡心暂时无法回复'
      const nextMessages = this.data.messages.slice()
      const assistantIndex = nextMessages.findIndex((item) => item.role === 'assistant' && !item.content)
      if (assistantIndex >= 0) {
        nextMessages[assistantIndex].content = message
        this.setData({ messages: nextMessages })
      } else {
        wx.showToast({ title: message, icon: 'none' })
      }
    } finally {
      this.setData({ streaming: false, composerStatus: '' })
    }
  },

  parseSseText(text) {
    const events = []
    const raw = String(text || '')
    raw.split('\n\n').forEach((block) => {
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
  },

  async archiveCurrentSession() {
    if (!this.data.currentSession) return
    try {
      await request({ url: `/duxin/sessions/${this.data.currentSession.id}/archive`, method: 'POST' })
      wx.showToast({ title: '已归档', icon: 'success' })
      this.setData({ currentSession: null, messages: [] })
      this.loadAll()
    } catch (error) {
      wx.showToast({ title: '归档失败', icon: 'none' })
    }
  },

  refreshData() {
    this.loadAll(false)
    if (this.data.currentSession) {
      this.openSession(this.data.currentSession.id)
    }
  },

  goForums() {
    wx.switchTab({ url: '/pages/forums/list/index' })
  },

  noop() {},
})
