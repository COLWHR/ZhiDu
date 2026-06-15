import { defineStore } from 'pinia'
import request from '@/utils/request'
import type {
  DuxinFeedback,
  DuxinFeedbackSummary,
  DuxinMemory,
  DuxinMemorySummary,
  DuxinMemoryType,
  DuxinMessage,
  DuxinTeamPlan,
  DuxinMode,
  DuxinRiskAssessment,
  DuxinSession
} from '@/types/duxin'

type StreamEvent = {
  type?: string
  content?: unknown
  session?: DuxinSession
  risk_level?: DuxinRiskAssessment['risk_level']
  signals?: string[]
  summary?: string
  response_mode?: DuxinRiskAssessment['response_mode']
  fallback?: boolean
  error?: boolean
  team?: DuxinTeamPlan
  [key: string]: unknown
}

const READ_HEADERS = { 'Cache-Control': 'no-store' }

const nowIso = () => new Date().toISOString()

const readResponseDetail = async (response: Response) => {
  const raw = await response.text().catch(() => '')
  if (!raw) return `Request failed: ${response.status}`

  try {
    const parsed = JSON.parse(raw)
    return typeof parsed?.detail === 'string' ? parsed.detail : raw
  } catch {
    return raw
  }
}

const initialState = () => ({
  sessions: [] as DuxinSession[],
  currentSession: null as DuxinSession | null,
  messages: [] as DuxinMessage[],
  memories: [] as DuxinMemory[],
  memorySummary: null as DuxinMemorySummary | null,
  feedbackEntries: [] as DuxinFeedback[],
  feedbackSummary: null as DuxinFeedbackSummary | null,
  teamPlan: null as DuxinTeamPlan | null,
  loading: false,
  streaming: false,
  error: null as string | null,
  composerStatus: '',
  riskLevel: 'L0' as DuxinSession['risk_level'],
  riskSummary: '',
  riskSignals: [] as string[],
  mode: 'support' as DuxinMode
})

export const useDuxinStore = defineStore('duxin', {
  state: () => initialState(),
  getters: {
    hasSession: state => !!state.currentSession,
    currentSessionTitle: state => state.currentSession?.title || '未命名会话'
  },
  actions: {
    reset() {
      Object.assign(this, initialState())
    },

    setMode(mode: DuxinMode) {
      this.mode = mode
    },

    hydrateTeamPlanFromMessages() {
      const latestTeamMessage = [...this.messages].reverse().find(message => !!message.metadata?.team)
      this.teamPlan = latestTeamMessage?.metadata?.team ?? null
    },

    updateSessionInList(session: DuxinSession) {
      const index = this.sessions.findIndex(item => item.id === session.id)
      if (index >= 0) {
        this.sessions[index] = session
      } else {
        this.sessions.unshift(session)
      }

      this.sessions.sort((a, b) => {
        const left = new Date(b.updated_at || b.created_at).getTime()
        const right = new Date(a.updated_at || a.created_at).getTime()
        return left - right
      })
    },

    async fetchSessions(autoOpen = true) {
      this.loading = true
      try {
        const res = await request.get('/duxin/sessions', { headers: READ_HEADERS })
        this.sessions = Array.isArray(res.data) ? (res.data as DuxinSession[]) : []

        if (autoOpen && !this.currentSession && this.sessions.length > 0) {
          await this.openSession(this.sessions[0].id)
        }
      } catch (error) {
        console.error('Failed to fetch duxin sessions:', error)
        this.sessions = []
      } finally {
        this.loading = false
      }
    },

    async createSession(payload?: { mode?: DuxinMode; title?: string; initial_message?: string }) {
      const body = {
        mode: payload?.mode || this.mode,
        title: payload?.title,
        initial_message: payload?.initial_message
      }

      const res = await request.post('/duxin/sessions', body)
      if (!res.data) {
        throw new Error('Failed to create duxin session')
      }

      const session = res.data as DuxinSession
      this.updateSessionInList(session)
      this.currentSession = session
      this.mode = session.mode
      this.riskLevel = session.risk_level

      if (payload?.initial_message) {
        await this.fetchMessages(session.id)
      } else {
        this.messages = []
        this.teamPlan = null
      }

      return session
    },

    async openSession(sessionId: number) {
      this.loading = true
      try {
        const [sessionRes, messagesRes] = await Promise.all([
          request.get(`/duxin/sessions/${sessionId}`, { headers: READ_HEADERS }),
          request.get(`/duxin/sessions/${sessionId}/messages`, { headers: READ_HEADERS })
        ])

        this.currentSession = sessionRes.data as DuxinSession
        this.mode = this.currentSession.mode
        this.riskLevel = this.currentSession.risk_level
        this.messages = Array.isArray(messagesRes.data) ? (messagesRes.data as DuxinMessage[]) : []
        this.hydrateTeamPlanFromMessages()
        this.error = null
        this.composerStatus = ''
      } catch (error) {
        console.error('Failed to open duxin session:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchMessages(sessionId: number) {
      const res = await request.get(`/duxin/sessions/${sessionId}/messages`, { headers: READ_HEADERS })
      this.messages = Array.isArray(res.data) ? (res.data as DuxinMessage[]) : []
      this.hydrateTeamPlanFromMessages()
    },

    async fetchMemories() {
      try {
        const res = await request.get('/duxin/memories', { headers: READ_HEADERS })
        this.memories = Array.isArray(res.data) ? (res.data as DuxinMemory[]) : []
      } catch (error) {
        console.error('Failed to fetch duxin memories:', error)
        this.memories = []
      }
    },

    async fetchMemorySummary() {
      try {
        const res = await request.get('/duxin/memories/summary', { headers: READ_HEADERS })
        this.memorySummary = res.data as DuxinMemorySummary
      } catch (error) {
        console.error('Failed to fetch duxin memory summary:', error)
        this.memorySummary = null
      }
    },

    async addMemory(payload: { memory_type: DuxinMemoryType; content: string; source_session_id?: number | null; user_editable?: boolean }) {
      const res = await request.post('/duxin/memories', payload)
      const memory = res.data as DuxinMemory
      this.memories.unshift(memory)
      return memory
    },

    async updateMemory(
      memoryId: number,
      payload: { memory_type?: DuxinMemoryType; content?: string; user_editable?: boolean }
    ) {
      const res = await request.patch(`/duxin/memories/${memoryId}`, payload)
      const memory = res.data as DuxinMemory
      const index = this.memories.findIndex(item => item.id === memory.id)
      if (index >= 0) {
        this.memories[index] = memory
      }
      return memory
    },

    async removeMemory(memoryId: number) {
      await request.delete(`/duxin/memories/${memoryId}`)
      this.memories = this.memories.filter(memory => memory.id !== memoryId)
    },

    async clearMemories() {
      await request.delete('/duxin/memories')
      this.memories = []
    },

    async fetchSafetyFeedback() {
      try {
        const res = await request.get('/duxin/safety/feedback', { headers: READ_HEADERS })
        this.feedbackEntries = Array.isArray(res.data) ? (res.data as DuxinFeedback[]) : []
      } catch (error) {
        console.error('Failed to fetch duxin feedback:', error)
        this.feedbackEntries = []
      }
    },

    async fetchSafetyFeedbackSummary() {
      try {
        const res = await request.get('/duxin/safety/feedback/summary', { headers: READ_HEADERS })
        this.feedbackSummary = res.data as DuxinFeedbackSummary
      } catch (error) {
        console.error('Failed to fetch duxin feedback summary:', error)
        this.feedbackSummary = null
      }
    },

    async submitSafetyFeedback(payload: {
      session_id?: number
      rating: string
      content?: string
      risk_level?: string
      save_as_memory?: boolean
      memory_type?: DuxinMemoryType
    }) {
      const res = await request.post('/duxin/safety/feedback', payload)
      const feedback = res.data as DuxinFeedback
      this.feedbackEntries.unshift(feedback)
      await Promise.all([this.fetchSafetyFeedbackSummary(), this.fetchMemorySummary(), this.fetchMemories()])
      return feedback
    },

    async archiveCurrentSession() {
      if (!this.currentSession) return
      const res = await request.post(`/duxin/sessions/${this.currentSession.id}/archive`)
      const archived = res.data as DuxinSession
      this.updateSessionInList(archived)
      this.currentSession = null
      this.messages = []
      this.teamPlan = null
      this.composerStatus = ''
      await Promise.all([this.fetchMemorySummary(), this.fetchSafetyFeedbackSummary()])
    },

    async sendMessage(content: string) {
      const text = content.trim()
      if (!text) return

      this.error = null

      if (!this.currentSession) {
        await this.createSession({
          mode: this.mode,
          title: text.slice(0, 18) || '渡心会话'
        })
      }

      const session = this.currentSession
      if (!session) {
        throw new Error('Unable to create duxin session')
      }

      const userMessage: DuxinMessage = {
        id: Date.now(),
        session_id: session.id,
        user_id: session.user_id,
        role: 'user',
        agent_name: '用户',
        content: text,
        risk_level: 'L0',
        metadata: this.teamPlan ? { team: this.teamPlan } : {},
        created_at: nowIso(),
        clientId: `user-${Date.now()}`
      }

      const assistantMessage: DuxinMessage = {
        id: Date.now() + 1,
        session_id: session.id,
        user_id: session.user_id,
        role: 'assistant',
        agent_name: '渡心主理人',
        content: '',
        risk_level: 'L0',
        metadata: {},
        created_at: nowIso(),
        clientId: `assistant-${Date.now()}`
      }

      this.messages.push(userMessage, assistantMessage)
      this.streaming = true
      this.composerStatus = '正在接住你的情绪...'
      this.riskLevel = session.risk_level

      try {
        const response = await fetch(`/api/v1/duxin/sessions/${session.id}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`
          },
          body: JSON.stringify({ content: text })
        })

        if (!response.ok) {
          throw new Error(await readResponseDetail(response))
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('未能读取渡心流式响应')
        }

        const decoder = new TextDecoder()
        let buffer = ''
        const assistantIndex = this.messages.findIndex(message => message.clientId === assistantMessage.clientId)

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n\n')
          buffer = parts.pop() || ''

          for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith('data: ')) continue

            const payloadText = line.slice(6).trim()
            if (!payloadText || payloadText === '[DONE]') continue

            let event: StreamEvent
            try {
              event = JSON.parse(payloadText)
            } catch {
              continue
            }

            switch (event.type) {
              case 'session':
                if (event.session) {
                  this.currentSession = event.session
                  this.updateSessionInList(event.session)
                }
                break
              case 'risk':
                if (typeof event.risk_level === 'string') {
                  this.riskLevel = event.risk_level
                }
                this.riskSummary = typeof event.summary === 'string' ? event.summary : this.riskSummary
                this.riskSignals = Array.isArray(event.signals) ? (event.signals as string[]) : this.riskSignals
                break
              case 'team':
                this.teamPlan = (event.team as DuxinTeamPlan) || null
                if (assistantIndex >= 0) {
                  this.messages[assistantIndex].metadata = {
                    ...(this.messages[assistantIndex].metadata || {}),
                    team: this.teamPlan
                  }
                }
                break
              case 'agent_status':
                this.composerStatus = typeof event.content === 'string' ? event.content : this.composerStatus
                break
              case 'chunk':
                if (assistantIndex >= 0 && typeof event.content === 'string') {
                  this.messages[assistantIndex].content += event.content
                }
                break
              case 'done':
                this.composerStatus = ''
                break
              case 'error':
                throw new Error(typeof event.content === 'string' ? event.content : '渡心回复失败')
              default:
                if (assistantIndex >= 0 && typeof event.content === 'string') {
                  this.messages[assistantIndex].content += event.content
                }
            }
          }
        }

        if (assistantIndex >= 0 && !this.messages[assistantIndex].content.trim()) {
          this.messages[assistantIndex].content = '我先陪你在这里停一下。你可以把此刻最重的那一块说给我听。'
        }

        await Promise.all([
          this.fetchSessions(),
          this.fetchMemories(),
          this.fetchMemorySummary(),
          this.fetchSafetyFeedback(),
          this.fetchSafetyFeedbackSummary()
        ])
      } catch (error) {
        const assistantIndex = this.messages.findIndex(message => message.clientId === assistantMessage.clientId)
        if (assistantIndex >= 0) {
          this.messages[assistantIndex].content = error instanceof Error ? error.message : '渡心回复失败，请稍后重试。'
        }
        this.error = error instanceof Error ? error.message : '渡心回复失败，请稍后重试。'
        throw error
      } finally {
        this.streaming = false
        this.composerStatus = ''
      }
    }
  }
})
