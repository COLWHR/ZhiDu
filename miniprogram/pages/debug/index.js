const requestModule = require('../../utils/request')
const config = require('../../utils/config')
const auth = require('../../utils/auth')

function stringify(value) {
  if (value == null) return ''
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch (err) {
    return String(value)
  }
}

function extractDetail(err) {
  if (!err) return ''

  const detail = err.data && err.data.detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item && (item.msg || item.message || item.detail))
      .filter(Boolean)
      .join('；')
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (err.data && typeof err.data.message === 'string' && err.data.message.trim()) {
    return err.data.message
  }

  if (typeof err.message === 'string' && err.message.trim()) {
    return err.message
  }

  if (typeof err.errMsg === 'string' && err.errMsg.trim()) {
    return err.errMsg
  }

  if (typeof err.statusCode === 'number') {
    return `HTTP ${err.statusCode}`
  }

  return '未知错误'
}

Page({
  data: {
    defaultApiBaseUrl: config.DEFAULT_API_BASE_URL,
    apiBaseUrl: '',
    storedApiBaseUrl: '',
    registerUrl: '',
    healthUrl: '',
    meUrl: '',
    cacheStatusText: '',
    cacheStatusClass: '',
    accessTokenState: '',
    refreshTokenState: '',
    testing: false,
    resultTypeText: '',
    resultTypeClass: '',
    resultText: '',
  },

  onLoad() {
    this.refreshState()
  },

  onShow() {
    this.refreshState()
  },

  refreshState() {
    const storedApiBaseUrl = wx.getStorageSync(config.storageKeys.apiBaseUrl) || ''
    const apiBaseUrl = config.getApiBaseUrl()
    const registerUrl = requestModule.buildUrl('/auth/register')
    const healthUrl = requestModule.buildUrl('/health')
    const meUrl = requestModule.buildUrl('/users/me')
    const hasAccessToken = Boolean(auth.getAccessToken())
    const hasRefreshToken = Boolean(auth.getRefreshToken())

    let cacheStatusText = '本地没有单独缓存'
    let cacheStatusClass = 'state-neutral'
    if (storedApiBaseUrl) {
      if (storedApiBaseUrl === apiBaseUrl) {
        cacheStatusText = '缓存与当前生效地址一致'
        cacheStatusClass = 'state-good'
      } else {
        cacheStatusText = '缓存与当前地址不一致，已回退默认值'
        cacheStatusClass = 'state-warn'
      }
    }

    this.setData({
      apiBaseUrl,
      storedApiBaseUrl,
      registerUrl,
      healthUrl,
      meUrl,
      cacheStatusText,
      cacheStatusClass,
      accessTokenState: hasAccessToken ? '已登录态' : '无 access token',
      refreshTokenState: hasRefreshToken ? '有 refresh token' : '无 refresh token',
    })
  },

  resetApiCache() {
    const app = getApp()
    if (app && typeof app.setApiBaseUrl === 'function') {
      app.setApiBaseUrl(config.DEFAULT_API_BASE_URL)
    } else {
      config.setApiBaseUrl(config.DEFAULT_API_BASE_URL)
    }
    wx.showToast({ title: '已恢复默认', icon: 'success' })
    this.refreshState()
  },

  async testConnectivity() {
    this.setData({
      testing: true,
      resultTypeText: '',
      resultTypeClass: '',
      resultText: '',
    })

    try {
      const res = await requestModule.request({
        url: '/health',
        method: 'GET',
      })

      const bodyText = stringify(res.data)
      this.setData({
        resultTypeText: '连通性正常',
        resultTypeClass: 'state-good',
        resultText: bodyText || '请求已成功到达服务器。',
      })
    } catch (err) {
      const statusCode = err && typeof err.statusCode === 'number' ? err.statusCode : null
      const detail = extractDetail(err)

      if (statusCode === 401) {
        this.setData({
          resultTypeText: '接口可达',
          resultTypeClass: 'state-warn',
          resultText: `${detail || 'HTTP 401'}\n说明请求已经到达服务器，只是当前未登录或 token 失效。`,
        })
      } else {
        this.setData({
          resultTypeText: '请求失败',
          resultTypeClass: 'state-bad',
          resultText: [
            detail,
            statusCode ? `HTTP ${statusCode}` : '',
            err && err.errMsg ? err.errMsg : '',
          ]
            .filter(Boolean)
            .join('\n'),
        })
      }
    } finally {
      this.setData({ testing: false })
    }
  },

  copyDebugInfo() {
    const payload = {
      defaultApiBaseUrl: this.data.defaultApiBaseUrl,
      apiBaseUrl: this.data.apiBaseUrl,
      storedApiBaseUrl: this.data.storedApiBaseUrl || '(empty)',
      registerUrl: this.data.registerUrl,
      healthUrl: this.data.healthUrl,
      meUrl: this.data.meUrl,
      accessTokenState: this.data.accessTokenState,
      refreshTokenState: this.data.refreshTokenState,
    }

    wx.setClipboardData({
      data: stringify(payload),
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' })
      },
    })
  },

  back() {
    wx.navigateBack()
  },
})
