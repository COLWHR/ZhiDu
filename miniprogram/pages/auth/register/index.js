const { request } = require('../../../utils/request')
const auth = require('../../../utils/auth')

function formatRegisterError(err) {
  const detail = err && err.data && err.data.detail

  if (Array.isArray(detail)) {
    const message = detail
      .map((item) => item && (item.msg || item.message || item.detail))
      .filter(Boolean)
      .join('；')
    if (message) return message
  }

  if (typeof detail === 'string' && detail.trim()) {
    if (detail === 'Username already registered') {
      return '用户名已存在'
    }
    return detail
  }

  if (err && err.data && typeof err.data.message === 'string' && err.data.message.trim()) {
    return err.data.message
  }

  if (err && typeof err.statusCode === 'number') {
    return `HTTP ${err.statusCode}`
  }

  if (err && (err.errMsg || err.message)) {
    return err.errMsg || err.message
  }

  return '注册失败'
}

Page({
  data: {
    username: '',
    password: '',
    confirmPassword: '',
    isPasswordVisible: false,
    isConfirmPasswordVisible: false,
    isAgreed: false,
    activeField: '',
    loading: false,
    error: '',
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  onFieldFocus(e) {
    this.setData({ activeField: e.currentTarget.dataset.field || '' })
  },

  onFieldBlur() {
    this.setData({ activeField: '' })
  },

  togglePassword() {
    this.setData({ isPasswordVisible: !this.data.isPasswordVisible })
  },

  toggleConfirmPassword() {
    this.setData({ isConfirmPasswordVisible: !this.data.isConfirmPasswordVisible })
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

  goLogin() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack()
      return
    }
    wx.redirectTo({ url: '/pages/auth/login/index' })
  },

  goToLogin() {
    this.goLogin()
  },

  handleRegister() {
    this.onSubmit()
  },

  async onSubmit() {
    const username = String(this.data.username || '').trim()
    const password = String(this.data.password || '')
    const confirmPassword = String(this.data.confirmPassword || '')

    if (!this.data.isAgreed) {
      this.setData({ error: '请先阅读并同意用户协议和隐私政策' })
      return
    }
    if (!username || !password || !confirmPassword) {
      this.setData({ error: '请输入账号和密码' })
      return
    }
    if (!/^[A-Za-z0-9]{4,20}$/.test(username)) {
      this.setData({ error: '账号需为 4-20 位字母或数字' })
      return
    }
    if (password.length < 6) {
      this.setData({ error: '密码至少 6 位' })
      return
    }
    if (password !== confirmPassword) {
      this.setData({ error: '两次输入的密码不一致' })
      return
    }

    this.setData({ loading: true, error: '' })
    try {
      await request({
        url: '/auth/register',
        method: 'POST',
        data: {
          username,
          password,
        },
        header: {
          'content-type': 'application/json',
        },
      })

      const loginRes = await request({
        url: '/auth/login',
        method: 'POST',
        data: {
          username,
          password,
        },
        header: {
          'content-type': 'application/x-www-form-urlencoded',
        },
      })
      auth.saveSession(loginRes.data, undefined)

      const meRes = await request({
        url: '/users/me',
        method: 'GET',
      })
      auth.setUser(meRes.data)

      wx.showToast({ title: '注册成功', icon: 'success' })
      wx.switchTab({ url: '/pages/home/index' })
    } catch (err) {
      const detail = formatRegisterError(err)
      console.error('Register failed:', err)
      this.setData({ error: detail })
    } finally {
      this.setData({ loading: false })
    }
  },
})
