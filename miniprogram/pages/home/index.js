const { request } = require('../../utils/request')
const auth = require('../../utils/auth')

Page({
  data: {
    user: { username: '' },
    forumCount: 0,
    personaCount: 0,
    activeForumCount: 0,
    recentForums: [],
    loading: false,
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }

    this.setData({ user: session.user || { username: '' } })
    this.loadDashboard()
  },

  async loadDashboard() {
    this.setData({ loading: true })
    try {
      const [forumRes, personaRes] = await Promise.all([
        request({ url: '/forums/', method: 'GET' }).catch(() => ({ data: [] })),
        request({ url: '/personas/', method: 'GET' }).catch(() => ({ data: [] })),
      ])

      const forums = Array.isArray(forumRes.data) ? forumRes.data : []
      const personas = Array.isArray(personaRes.data) ? personaRes.data : []

      this.setData({
        forumCount: forums.length,
        personaCount: personas.length,
        activeForumCount: forums.filter((item) => item.status === 'running' || item.status === 'active').length,
        recentForums: forums.slice(0, 4).map((item) => ({
          ...item,
          statusText: this.formatStatus(item.status),
          startTimeText: this.formatDate(item.start_time),
        })),
      })
    } catch (err) {
      wx.showToast({ title: '首页数据加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  goForums() {
    wx.switchTab({ url: '/pages/forums/list/index' })
  },

  goPersonas() {
    wx.switchTab({ url: '/pages/personas/index' })
  },

  goNuwa() {
    wx.navigateTo({ url: '/pages/nuwa/index' })
  },

  goAssistant() {
    wx.navigateTo({ url: '/pages/assistant/index' })
  },

  goDuxin() {
    wx.switchTab({ url: '/pages/duxin/index' })
  },

  goCreateForum() {
    wx.navigateTo({ url: '/pages/forums/create/index' })
  },

  handleCreateForum() {
    this.goCreateForum()
  },

  goForumDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/forums/detail/index?id=${id}` })
  },

  goToLogin() {
    if (this.data.user && this.data.user.username) return
    wx.navigateTo({ url: '/pages/auth/login/index' })
  },

  goToMyAgents() {
    this.goPersonas()
  },

  goToFavorites() {
    wx.showToast({ title: '收藏功能暂未开放', icon: 'none' })
  },

  goToHistory() {
    this.goForums()
  },

  goToDownloads() {
    wx.showToast({ title: '暂无下载内容', icon: 'none' })
  },

  goToMessages() {
    this.goForums()
  },

  goToFeedback() {
    wx.showToast({ title: '反馈功能暂未开放', icon: 'none' })
  },

  goToAbout() {
    wx.showToast({ title: 'ZhiDo 智能协作小程序', icon: 'none' })
  },

  goToSettings() {
    wx.showActionSheet({
      itemList: ['退出登录'],
      success: () => this.logout(),
    })
  },

  logout() {
    auth.clearSession()
    wx.reLaunch({ url: '/pages/auth/login/index' })
  },

  handleLogout() {
    this.logout()
  },

  formatStatus(status) {
    switch (status) {
      case 'running':
      case 'active':
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

  formatDate(value) {
    if (!value) return ''
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return String(value)
    return date.toLocaleString('zh-CN', { hour12: false })
  },
})
