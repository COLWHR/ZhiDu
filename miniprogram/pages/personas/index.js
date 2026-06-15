const { request } = require('../../utils/request')
const auth = require('../../utils/auth')

const emptyForm = () => ({
  name: '',
  title: '',
  bio: '',
  theoriesStr: '',
  stance: '',
  system_prompt: '',
  is_public: false,
})

Page({
  data: {
    personas: [],
    filteredPersonas: [],
    loading: false,
    saving: false,
    showForm: false,
    detailPersona: null,
    editingId: 0,
    searchText: '',
    form: emptyForm(),
  },

  onShow() {
    const session = auth.readSession()
    if (!session.accessToken) {
      wx.redirectTo({ url: '/pages/auth/login/index' })
      return
    }
    this.loadPersonas()
  },

  async loadPersonas() {
    this.setData({ loading: true })
    try {
      const res = await request({ url: '/personas/', method: 'GET' })
      const personas = Array.isArray(res.data) ? res.data.map((item) => ({
        ...item,
        is_public: false,
        theoriesText: Array.isArray(item.theories) ? item.theories.join('、') : '',
      })) : []
      this.setData({ personas }, () => this.updateFilteredPersonas())
    } catch (err) {
      wx.showToast({ title: '加载智能体失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearchInput(e) {
    this.setData({ searchText: e.detail.value }, () => this.updateFilteredPersonas())
  },

  updateFilteredPersonas() {
    const keyword = String(this.data.searchText || '').trim().toLowerCase()
    const filteredPersonas = !keyword
      ? this.data.personas
      : this.data.personas.filter((item) => [item.name, item.title, item.bio, item.stance].join(' ').toLowerCase().includes(keyword))
    this.setData({ filteredPersonas })
  },

  openCreate() {
    this.setData({
      showForm: true,
      editingId: 0,
      detailPersona: null,
      form: emptyForm(),
    })
  },

  openEdit(e) {
    const id = Number(e.currentTarget.dataset.id)
    const persona = this.data.personas.find((item) => item.id === id)
    if (!persona) return
    this.setData({
      showForm: true,
      detailPersona: null,
      editingId: persona.id,
      form: {
        name: persona.name || '',
        title: persona.title || '',
        bio: persona.bio || '',
        theoriesStr: Array.isArray(persona.theories) ? persona.theories.join(', ') : '',
        stance: persona.stance || '',
        system_prompt: persona.system_prompt || '',
        is_public: false,
      },
    })
  },

  showDetail(e) {
    const id = Number(e.currentTarget.dataset.id)
    const persona = this.data.personas.find((item) => item.id === id)
    if (!persona) return
    this.setData({ detailPersona: persona, showForm: false })
  },

  closePanels() {
    this.setData({ showForm: false, detailPersona: null })
  },

  noop() {},

  onFormInput(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ [`form.${key}`]: e.detail.value })
  },

  onPublicChange(e) {
    this.setData({ 'form.is_public': !!e.detail.value.length })
  },

  async savePersona() {
    const form = this.data.form
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入名称', icon: 'none' })
      return
    }

    this.setData({ saving: true })
    try {
      const payload = {
        name: form.name.trim(),
        title: form.title.trim(),
        bio: form.bio.trim(),
        stance: form.stance.trim(),
        system_prompt: form.system_prompt.trim(),
        theories: form.theoriesStr.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
        is_public: false,
      }

      if (this.data.editingId) {
        await request({
          url: `/personas/${this.data.editingId}`,
          method: 'PUT',
          data: payload,
          header: { 'content-type': 'application/json' },
        })
        wx.showToast({ title: '更新成功', icon: 'success' })
      } else {
        await request({
          url: '/personas/',
          method: 'POST',
          data: payload,
          header: { 'content-type': 'application/json' },
        })
        wx.showToast({ title: '创建成功', icon: 'success' })
      }

      this.closePanels()
      this.loadPersonas()
    } catch (err) {
      const detail = err && err.data && err.data.detail ? err.data.detail : '保存失败'
      wx.showToast({ title: detail, icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },

  async deletePersona(e) {
    const id = Number(e.currentTarget.dataset.id)
    const persona = this.data.personas.find((item) => item.id === id)
    if (!persona) return

    wx.showModal({
      title: '删除智能体',
      content: `确认删除 ${persona.name} 吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await request({ url: `/personas/${id}`, method: 'DELETE' })
          wx.showToast({ title: '删除成功', icon: 'success' })
          if (this.data.detailPersona && this.data.detailPersona.id === id) {
            this.setData({ detailPersona: null })
          }
          this.loadPersonas()
        } catch (error) {
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      },
    })
  },

  async createPresets() {
    try {
      await request({ url: '/personas/batch/preset', method: 'POST' })
      wx.showToast({ title: '已生成预置智能体', icon: 'success' })
      this.loadPersonas()
    } catch (error) {
      const detail = error && error.data && error.data.detail ? error.data.detail : '生成失败'
      wx.showToast({ title: detail, icon: 'none' })
    }
  },

  goAssistant() {
    wx.navigateTo({ url: '/pages/assistant/index' })
  },

  goNuwa() {
    wx.navigateTo({ url: '/pages/nuwa/index' })
  },

  goForums() {
    wx.switchTab({ url: '/pages/forums/list/index' })
  },
})
