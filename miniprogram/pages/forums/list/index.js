const { request } = require('../../../utils/request')
const auth = require('../../../utils/auth')

const FORUM_GROUPS = [
  {
    key: 'running',
    label: '进行中',
    description: '正在进行中的论坛',
    emptyText: '当前没有正在进行的论坛',
    statuses: ['running', 'active'],
  },
  {
    key: 'pending',
    label: '未开始',
    description: '等待开始的论坛',
    emptyText: '当前没有未开始的论坛',
    statuses: ['pending'],
  },
  {
    key: 'finished',
    label: '已结束',
    description: '已经关闭或完成的论坛',
    emptyText: '当前没有已结束的论坛',
    statuses: ['closed', 'finished'],
  },
]

Page({
  data: {
    forums: [],
    forumGroups: [],
    forumSummary: {
      total: 0,
      running: 0,
      pending: 0,
      finished: 0,
    },
    loading: false,
    error: '',
    showDeleteConfirm: false,
    deleting: false,
    pendingDeleteForum: null,
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }
    this.loadForums()
  },

  normalizeStatus(status) {
    switch (status) {
      case 'running':
      case 'active':
        return 'running'
      case 'pending':
        return 'pending'
      case 'closed':
      case 'finished':
        return 'finished'
      default:
        return 'finished'
    }
  },

  buildForumGroups(forums) {
    return FORUM_GROUPS.map((group) => {
      const items = forums.filter((item) => group.statuses.includes(this.normalizeStatus(item.status)))
      return {
        ...group,
        items,
        count: items.length,
      }
    })
  },

  buildForumSummary(forums) {
    return forums.reduce(
      (acc, item) => {
        const status = this.normalizeStatus(item.status)
        acc.total += 1
        if (status === 'running') acc.running += 1
        if (status === 'pending') acc.pending += 1
        if (status === 'finished') acc.finished += 1
        return acc
      },
      {
        total: 0,
        running: 0,
        pending: 0,
        finished: 0,
      },
    )
  },

  async loadForums() {
    this.setData({ loading: true, error: '' })
    try {
      const res = await request({
        url: '/forums/',
        method: 'GET',
      })

      const forums = Array.isArray(res.data)
        ? res.data.map((item) => ({
            ...item,
            participantCount: Array.isArray(item.participants) ? item.participants.length : 0,
            statusText: this.formatStatus(item.status),
            startTimeText: this.formatDate(item.start_time),
          }))
        : []

      this.setData({
        forums,
        forumGroups: this.buildForumGroups(forums),
        forumSummary: this.buildForumSummary(forums),
      })
    } catch (err) {
      if (err && err.statusCode === 401) {
        wx.redirectTo({ url: '/pages/auth/login/index' })
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '加载论坛失败'
      this.setData({ error: detail })
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onRefresh() {
    this.loadForums()
  },

  goCreate() {
    wx.navigateTo({ url: '/pages/forums/create/index' })
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/forums/detail/index?id=${id}` })
  },

  handleDelete(e) {
    const id = Number(e.currentTarget.dataset.id || 0)
    if (!id) return

    const item = this.data.forums.find((forum) => forum.id === id)
    this.setData({
      showDeleteConfirm: true,
      pendingDeleteForum: item || { id, topic: '' },
    })
  },

  cancelDelete() {
    if (this.data.deleting) return
    this.setData({
      showDeleteConfirm: false,
      pendingDeleteForum: null,
    })
  },

  noop() {},

  async confirmDelete() {
    const item = this.data.pendingDeleteForum
    const id = item && item.id ? Number(item.id) : 0
    if (!id || this.data.deleting) return

    this.setData({ deleting: true })
    try {
      await request({
        url: `/forums/${id}`,
        method: 'DELETE',
      })
      wx.showToast({ title: '删除成功', icon: 'success' })
      this.setData({
        showDeleteConfirm: false,
        pendingDeleteForum: null,
      })
      await this.loadForums()
    } catch (err) {
      if (err && err.statusCode === 404) {
        wx.showToast({ title: '论坛已删除', icon: 'success' })
        this.setData({
          showDeleteConfirm: false,
          pendingDeleteForum: null,
        })
        await this.loadForums()
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '删除失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ deleting: false })
    }
  },

  formatStatus(status) {
    switch (this.normalizeStatus(status)) {
      case 'running':
        return '进行中'
      case 'pending':
        return '未开始'
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
