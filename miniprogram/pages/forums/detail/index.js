const { request } = require('../../../utils/request')
const { connectForumSocket } = require('../../../utils/socket')
const config = require('../../../utils/config')
const auth = require('../../../utils/auth')

Page({
  data: {
    forumId: 0,
    forum: {},
    messages: [],
    inputValue: '',
    loading: false,
    sending: false,
    starting: false,
    scrollIntoView: '',
    statusText: '',
    forumStartTimeText: '未设置',
    user: null,
    inputFocused: false,
    participantLabels: ['全体参与者'],
    participantIds: [0],
    participantPickerIndex: 0,
    selectedPersonaId: 0,
    selectedPersonaName: '全体参与者',
  },

  onLoad(options) {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }

    const forumId = Number(options.id || 0)
    this.setData({ forumId })
    this.loadForum()
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
    }
  },

  onUnload() {
    this.teardownSocket()
  },

  teardownSocket() {
    if (this.socketHeartbeat) {
      clearInterval(this.socketHeartbeat)
      this.socketHeartbeat = null
    }
    if (this.socketTask) {
      try {
        this.socketTask.close()
      } catch (err) {
        // ignore
      }
      this.socketTask = null
    }
  },

  getStatusText(status) {
    switch (status) {
      case 'running':
        return '进行中'
      case 'pending':
        return '未开始'
      case 'closed':
      case 'finished':
        return '已结束'
      default:
        return status || '未知'
    }
  },

  formatDateTime(value) {
    if (!value) return '未设置'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    const pad = (num) => String(num).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  },

  getAvatarLabel(name) {
    const value = String(name || '?').trim()
    return value ? value.slice(0, 1) : '?'
  },

  isImageContent(content) {
    return typeof content === 'string' && /\/uploads\/.+\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(content)
  },

  resolveMediaUrl(content) {
    const value = String(content || '').trim()
    if (!value) return value
    if (/^https?:\/\//i.test(value)) return value
    if (/^\/uploads\/.+\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(value)) {
      return `${config.getServerOrigin()}${value}`
    }
    return value
  },

  decorateMessage(message, expanded = false) {
    const content = String(message.content || '')
    const renderedContent = message.type === 'image' ? this.resolveMediaUrl(content) : content
    const isLong = message.type !== 'image' && renderedContent.length > 86
    return {
      ...message,
      content: renderedContent,
      expanded: !!expanded,
      isLong,
      previewContent: isLong ? `${renderedContent.slice(0, 86)}...` : renderedContent,
    }
  },

  normalizeMessages(list, user) {
    return list.map((item, index) => {
      const message = {
        ...item,
        key: item.id ? `msg-${item.id}` : `msg-${index}-${Date.now()}`,
        isSelf: user ? item.speaker_name === user.username : false,
        pending: false,
        type: this.isImageContent(item.content) ? 'image' : 'text',
        avatarLabel: user && item.speaker_name === user.username ? '我' : this.getAvatarLabel(item.speaker_name),
      }
      return this.decorateMessage(message)
    })
  },

  buildParticipantOptions(forum) {
    const participants = Array.isArray(forum.participants) ? forum.participants : []
    const labels = ['全体参与者']
    const ids = [0]

    participants.forEach((item, index) => {
      const persona = item && item.persona ? item.persona : null
      const name = persona && persona.name ? persona.name : `参与者${index + 1}`
      labels.push(name)
      ids.push(Number(item.persona_id || 0))
    })

    this.setData({
      participantLabels: labels,
      participantIds: ids,
      participantPickerIndex: 0,
      selectedPersonaId: 0,
      selectedPersonaName: '全体参与者',
    })
  },

  onParticipantChange(e) {
    const index = Number(e.detail.value || 0)
    const ids = this.data.participantIds || [0]
    const labels = this.data.participantLabels || ['全体参与者']
    const selectedPersonaId = Number(ids[index] || 0)
    const selectedPersonaName = labels[index] || '全体参与者'

    this.setData({
      participantPickerIndex: index,
      selectedPersonaId,
      selectedPersonaName,
    })
  },

  async handleStart() {
    if (this.data.starting || this.data.forum.status !== 'pending') return

    this.setData({ starting: true })
    try {
      await request({
        url: `/forums/${this.data.forumId}/start`,
        method: 'POST',
      })

      this.setData({
        forum: { ...this.data.forum, status: 'running' },
        statusText: this.getStatusText('running'),
        inputFocused: true,
      })

      wx.showToast({ title: '论坛已开启', icon: 'success' })
      this.connectSocket()
      this.syncMessages()
    } catch (err) {
      const detail = err && err.data && err.data.detail ? err.data.detail : '开启论坛失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ starting: false })
    }
  },

  async confirmDelete() {
    return new Promise((resolve) => {
      wx.showModal({
        title: '删除论坛',
        content: `确定删除“${this.data.forum.topic || '该论坛'}”吗？`,
        confirmText: '删除',
        confirmColor: '#dc2626',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false),
      })
    })
  },

  async handleDelete() {
    const confirmed = await this.confirmDelete()
    if (!confirmed) return

    const backToList = () => {
      const pages = getCurrentPages()
      if (pages.length > 1) {
        wx.navigateBack({ delta: 1 })
      } else {
        wx.redirectTo({ url: '/pages/forums/list/index' })
      }
    }

    try {
      await request({
        url: `/forums/${this.data.forumId}`,
        method: 'DELETE',
      })
      this.teardownSocket()
      wx.showToast({ title: '删除成功', icon: 'success' })
      setTimeout(() => {
        backToList()
      }, 300)
    } catch (err) {
      if (err && err.statusCode === 404) {
        this.teardownSocket()
        wx.showToast({ title: '论坛已删除', icon: 'success' })
        setTimeout(() => {
          backToList()
        }, 300)
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '删除失败'
      wx.showToast({ title: detail, icon: 'none' })
    }
  },

  appendLocalMessage(content, speaker, isSelf, extra = {}) {
    const tempMessage = this.decorateMessage({
      id: `temp-${Date.now()}-${Math.random()}`,
      key: `temp-${Date.now()}-${Math.random()}`,
      forum_id: this.data.forumId,
      persona_id: extra.persona_id || 0,
      moderator_id: null,
      speaker_name: speaker,
      content,
      thought: extra.thought || null,
      timestamp: new Date().toISOString(),
      pending: true,
      failed: false,
      isSelf: !!isSelf,
      type: this.isImageContent(content) ? 'image' : 'text',
      avatarLabel: isSelf ? '我' : this.getAvatarLabel(speaker),
    })

    this.setData(
      {
        messages: this.data.messages.concat(tempMessage),
      },
      () => this.scrollToBottom(),
    )

    return tempMessage
  },

  async loadForum() {
    this.setData({ loading: true })
    try {
      const [forumRes, messageRes] = await Promise.all([
        request({ url: `/forums/${this.data.forumId}`, method: 'GET' }),
        request({ url: `/forums/${this.data.forumId}/messages`, method: 'GET' }).catch(() => ({ data: [] })),
      ])

      const forum = forumRes.data || {}
      const user = auth.readSession().user || null
      const messages = this.normalizeMessages(Array.isArray(messageRes.data) ? messageRes.data : [], user)

      this.setData({
        forum,
        messages,
        user,
        statusText: this.getStatusText(forum.status),
        forumStartTimeText: this.formatDateTime(forum.start_time),
        inputFocused: forum.status === 'running',
      })
      this.buildParticipantOptions(forum)

      this.scrollToBottom()
      this.connectSocket()
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '加载论坛失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  connectSocket() {
    this.teardownSocket()

    this.socketTask = connectForumSocket(this.data.forumId, {
      onOpen: () => {
        this.socketHeartbeat = setInterval(() => {
          if (this.socketTask) {
            try {
              this.socketTask.send({
                data: 'ping',
              })
            } catch (err) {
              // ignore
            }
          }
        }, 30000)
      },
      onClose: () => {
        if (this.socketHeartbeat) {
          clearInterval(this.socketHeartbeat)
          this.socketHeartbeat = null
        }
      },
      onError: () => {
        wx.showToast({ title: '实时连接失败，已使用接口同步', icon: 'none' })
      },
      onMessage: (payload) => {
        if (!payload || payload === 'pong') return
        if (payload.type === 'new_message' && payload.data) {
          this.mergeIncomingMessage(payload.data)
          return
        }
        if (payload.type === 'message_chunk' && payload.data) {
          this.mergeStreamingChunk(payload.data)
          return
        }
      },
    })
  },

  mergeIncomingMessage(message) {
    const incoming = this.decorateMessage({
      ...message,
      key: message.id ? `msg-${message.id}` : `msg-${Date.now()}-${Math.random()}`,
      isSelf: this.data.user ? message.speaker_name === this.data.user.username : false,
      pending: false,
      type: this.isImageContent(message.content) ? 'image' : 'text',
      avatarLabel: this.data.user && message.speaker_name === this.data.user.username ? '我' : this.getAvatarLabel(message.speaker_name),
    })

    const messages = this.data.messages.slice()
    const streamIndex = incoming.stream_id
      ? messages.findIndex((item) => item.stream_id === incoming.stream_id)
      : -1
    const pendingIndex = messages.findIndex((item) => item.pending && item.speaker_name === incoming.speaker_name)

    if (streamIndex >= 0) {
      messages.splice(streamIndex, 1, this.decorateMessage(incoming, messages[streamIndex].expanded))
    } else if (pendingIndex >= 0) {
      messages.splice(pendingIndex, 1, incoming)
    } else if (!messages.some((item) => item.id && incoming.id && item.id === incoming.id)) {
      messages.push(incoming)
    }

    this.setData({ messages }, () => this.scrollToBottom())
  },

  mergeStreamingChunk(chunk) {
    const messages = this.data.messages.slice()
    let target = null

    if (chunk.stream_id) {
      target = messages.find((item) => item.stream_id === chunk.stream_id)
    }

    if (!target && messages.length) {
      const last = messages[messages.length - 1]
      if (last && last.speaker_name === chunk.speaker_name) {
        target = last
      }
    }

    if (target) {
      target.content = `${target.content || ''}${chunk.content || ''}`
      target.type = this.isImageContent(target.content) ? 'image' : 'text'
      Object.assign(target, this.decorateMessage(target, target.expanded))
      if (chunk.stream_id && !target.stream_id) {
        target.stream_id = chunk.stream_id
      }
    } else {
      messages.push(this.decorateMessage({
        ...chunk,
        key: `stream-${Date.now()}-${Math.random()}`,
        isSelf: false,
        pending: false,
        type: this.isImageContent(chunk.content) ? 'image' : 'text',
        avatarLabel: this.getAvatarLabel(chunk.speaker_name),
        stream_id: chunk.stream_id || null,
      }))
    }

    this.setData({ messages }, () => this.scrollToBottom())
  },

  toggleMessageDetail(e) {
    const key = e.currentTarget.dataset.key
    const messages = this.data.messages.map((item) => {
      if (item.key !== key) return item
      return this.decorateMessage(item, !item.expanded)
    })
    this.setData({ messages })
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  async sendContent(content) {
    const user = this.data.user || auth.readSession().user || {}
    const speaker = user.username || '观众'
    const wasPending = this.data.forum && this.data.forum.status === 'pending'
    if (this.data.selectedPersonaId === 0 && wasPending) {
      wx.showToast({ title: '请先开启论坛，再发送给全体参与者', icon: 'none' })
      return
    }

    const tempMessage = this.appendLocalMessage(content, speaker, true)

    try {
      if (this.data.selectedPersonaId > 0) {
        const response = await request({
          url: `/forums/${this.data.forumId}/ask`,
          method: 'POST',
          data: {
            persona_id: this.data.selectedPersonaId,
            content,
            speaker,
          },
          header: {
            'content-type': 'application/json',
          },
        })

        if (response && response.data) {
          const answer = response.data
          const fallbackAnswer = '暂时没有拿到有效回复，请稍后再试。'
          const assistantMessage = this.decorateMessage({
            id: answer.id || `assistant-${Date.now()}`,
            key: answer.id ? `msg-${answer.id}` : `assistant-${Date.now()}`,
            forum_id: answer.forum_id || this.data.forumId,
            persona_id: answer.persona_id || this.data.selectedPersonaId,
            moderator_id: answer.moderator_id || null,
            speaker_name: answer.speaker_name || this.data.selectedPersonaName,
            content: answer.content || fallbackAnswer,
            thought: answer.thought || null,
            timestamp: answer.timestamp || new Date().toISOString(),
            pending: false,
            isSelf: false,
            type: this.isImageContent(answer.content) ? 'image' : 'text',
            avatarLabel: this.getAvatarLabel(answer.speaker_name || this.data.selectedPersonaName),
          })

          const nextMessages = this.data.messages.slice()
          const userIndex = nextMessages.findIndex((item) => item.key === tempMessage.key)
          if (userIndex >= 0) {
            nextMessages[userIndex] = { ...nextMessages[userIndex], pending: false }
          }

          const existingIndex = nextMessages.findIndex(
            (item) => item.id && assistantMessage.id && item.id === assistantMessage.id,
          )
          const placeholderIndex = nextMessages.findIndex(
            (item) => !item.id && item.speaker_name === assistantMessage.speaker_name,
          )

          if (existingIndex >= 0) {
            nextMessages[existingIndex] = {
              ...nextMessages[existingIndex],
              ...assistantMessage,
            }
          } else if (placeholderIndex >= 0) {
            nextMessages[placeholderIndex] = assistantMessage
          } else {
            nextMessages.push(assistantMessage)
          }

          this.setData({ messages: nextMessages }, () => this.scrollToBottom())
        }

        wx.showToast({ title: `消息已发给 ${this.data.selectedPersonaName}`, icon: 'none' })
      } else {
        if (wasPending) {
          try {
            await request({
              url: `/forums/${this.data.forumId}/start`,
              method: 'POST',
            })
            this.setData({
              forum: { ...this.data.forum, status: 'running' },
              statusText: this.getStatusText('running'),
            })
          } catch (startErr) {
            wx.showToast({ title: '论坛尚未开始，消息已发送到队列', icon: 'none' })
          }
        }

        await request({
          url: `/forums/${this.data.forumId}/chat`,
          method: 'POST',
          data: {
            speaker,
            content,
          },
          header: {
            'content-type': 'application/json',
          },
        })
        wx.showToast({ title: '发送成功', icon: 'success' })
      }

    setTimeout(() => this.syncMessages(), 1200)
    setTimeout(() => this.syncMessages(), 2600)
    } catch (error) {
      const messages = this.data.messages.map((item) => {
        if (item.key !== tempMessage.key) return item
        return {
          ...item,
          pending: false,
          failed: true,
        }
      })
      this.setData({ messages }, () => this.scrollToBottom())
      throw error
    }
  },

  async onSend() {
    const content = (this.data.inputValue || '').trim()
    if (!content || this.data.sending) return

    this.setData({
      sending: true,
      inputValue: '',
    })

    try {
      await this.sendContent(content)
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '发送失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ sending: false, inputFocused: true })
    }
  },

  async syncMessages() {
    try {
      const res = await request({
        url: `/forums/${this.data.forumId}/messages`,
        method: 'GET',
      })
      const user = auth.readSession().user || null
      const messages = this.normalizeMessages(Array.isArray(res.data) ? res.data : [], user)
      this.setData({ messages }, () => this.scrollToBottom())
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
      }
    }
  },

  scrollToBottom() {
    const last = this.data.messages[this.data.messages.length - 1]
    if (last && last.key) {
      this.setData({ scrollIntoView: last.key })
    }
  },
})
