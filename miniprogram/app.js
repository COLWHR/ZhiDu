const config = require('./utils/config')

App({
  globalData: {
    apiBaseUrl: config.getApiBaseUrl(),
    user: null,
  },

  onLaunch() {
    const currentApiBaseUrl = config.getApiBaseUrl()
    if (this.globalData.apiBaseUrl !== currentApiBaseUrl) {
      this.globalData.apiBaseUrl = currentApiBaseUrl
    }

    const storedApiBaseUrl = wx.getStorageSync(config.storageKeys.apiBaseUrl)
    if (storedApiBaseUrl !== currentApiBaseUrl) {
      wx.setStorageSync(config.storageKeys.apiBaseUrl, currentApiBaseUrl)
    }

    const user = wx.getStorageSync(config.storageKeys.user)
    if (user) {
      this.globalData.user = user
    }
  },

  setApiBaseUrl(url) {
    config.setApiBaseUrl(url)
    this.globalData.apiBaseUrl = config.getApiBaseUrl()
  },

  setUser(user) {
    this.globalData.user = user || null
    if (user) {
      wx.setStorageSync(config.storageKeys.user, user)
    } else {
      wx.removeStorageSync(config.storageKeys.user)
    }
  },
})
