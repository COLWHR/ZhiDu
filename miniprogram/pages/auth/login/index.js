const { request } = require('../../../utils/request')
const auth = require('../../../utils/auth')

Page({
  data: {
    username: '',
    password: '',
    isAgreed: false,
    loading: false,
    error: '',
  },

  onShow() {
    const session = auth.readSession()
    if (session.accessToken) {
      wx.switchTab({ url: '/pages/home/index' })
    }
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  goRegister() {
    wx.navigateTo({ url: '/pages/auth/register/index' })
  },

  toggleAgreement() {
    this.setData({ isAgreed: !this.data.isAgreed })
  },

  goUserProtocol() {
    wx.navigateTo({ url: '/pages/legal/index?type=agreement' })
  },

  goPrivacyPolicy() {
    wx.navigateTo({ url: '/pages/legal/index?type=privacy' })
  },

  handleLogin() {
    if (!this.data.isAgreed) {
      this.setData({ error: '请先阅读并同意用户协议和隐私政策' })
      return
    }
    this.onSubmit()
  },

  async onSubmit() {
    if (!this.data.username || !this.data.password) {
      this.setData({ error: '请输入用户名和密码' })
      return
    }

    this.setData({ loading: true, error: '' })
    try {
      const res = await request({
        url: '/auth/login',
        method: 'POST',
        data: {
          username: this.data.username,
          password: this.data.password,
        },
        header: {
          'content-type': 'application/x-www-form-urlencoded',
        },
      })

      auth.saveSession(res.data, undefined)

      const meRes = await request({
        url: '/users/me',
        method: 'GET',
      })
      auth.setUser(meRes.data)

      wx.showToast({ title: '登录成功', icon: 'success' })
      wx.switchTab({ url: '/pages/home/index' })
    } catch (err) {
      if (err && err.statusCode === 401) {
        this.setData({ error: '用户名或密码错误' })
        return
      }
      const detail = err && err.data && err.data.detail ? err.data.detail : '登录失败'
      this.setData({ error: detail })
    } finally {
      this.setData({ loading: false })
    }
  },
})
