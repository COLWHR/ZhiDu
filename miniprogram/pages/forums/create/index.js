const { request } = require('../../../utils/request')
const auth = require('../../../utils/auth')

Page({
  data: {
    topic: '',
    duration: 30,
    personas: [],
    moderators: [],
    moderatorNames: ['不指定'],
    moderatorIndex: 0,
    selectedPersonaIds: [],
    loading: false,
    error: '',
  },

  onLoad() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }
    this.loadOptions()
  },

  async loadOptions() {
    try {
      const [personaRes, moderatorRes] = await Promise.all([
        request({ url: '/personas/', method: 'GET' }).catch(() => ({ data: [] })),
        request({ url: '/moderators/', method: 'GET' }).catch(() => ({ data: [] })),
      ])

      const personas = Array.isArray(personaRes.data)
        ? personaRes.data.map((item) => ({
            ...item,
            selected: false,
          }))
        : []
      const moderators = Array.isArray(moderatorRes.data) ? moderatorRes.data : []

      this.setData({
        personas,
        moderators,
        moderatorNames: ['不指定'].concat(moderators.map((item) => item.name)),
      })
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
        return
      }
      this.setData({ error: '加载可选项失败' })
    }
  },

  onTopicInput(e) {
    this.setData({ topic: e.detail.value })
  },

  onDurationInput(e) {
    this.setData({ duration: Number(e.detail.value || 30) })
  },

  onModeratorChange(e) {
    this.setData({ moderatorIndex: Number(e.detail.value || 0) })
  },

  togglePersona(e) {
    const id = Number(e.currentTarget.dataset.id)
    const selectedPersonaIds = this.data.selectedPersonaIds.slice()
    const index = selectedPersonaIds.indexOf(id)

    if (index >= 0) {
      selectedPersonaIds.splice(index, 1)
    } else {
      selectedPersonaIds.push(id)
    }

    const personas = this.data.personas.map((item) => ({
      ...item,
      selected: selectedPersonaIds.includes(item.id),
    }))

    this.setData({ selectedPersonaIds, personas })
  },

  async onSubmit() {
    if (!this.data.topic.trim()) {
      this.setData({ error: '请输入论坛主题' })
      return
    }
    if (!this.data.selectedPersonaIds.length) {
      this.setData({ error: '请至少选择一个参与者' })
      return
    }

    const moderator = this.data.moderatorIndex > 0 ? this.data.moderators[this.data.moderatorIndex - 1] : null

    this.setData({ loading: true, error: '' })
    try {
      const res = await request({
        url: '/forums/',
        method: 'POST',
        data: {
          topic: this.data.topic.trim(),
          participant_ids: this.data.selectedPersonaIds,
          moderator_id: moderator ? moderator.id : null,
          duration_minutes: this.data.duration || 30,
        },
        header: {
          'content-type': 'application/json',
        },
      })

      wx.showToast({ title: '创建成功', icon: 'success' })
      wx.redirectTo({ url: `/pages/forums/detail/index?id=${res.data.id}` })
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '创建失败'
      this.setData({ error: detail })
    } finally {
      this.setData({ loading: false })
    }
  },
})
