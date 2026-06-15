const config = require('./config')
const auth = require('./auth')

let refreshPromise = null

function buildUrl(path) {
  const suffix = String(path || '').replace(/^\//, '')
  return `${config.getApiBaseUrl()}/${suffix}`
}

function serializeForm(data) {
  return Object.keys(data || {})
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(data[key] == null ? '' : data[key])}`)
    .join('&')
}

function parseResponseData(res) {
  if (res && typeof res.data === 'string') {
    try {
      return JSON.parse(res.data)
    } catch (err) {
      return res.data
    }
  }
  return res ? res.data : undefined
}

function normalizeRequestError(err, responseData, response) {
  const error = {
    message: err && (err.message || err.errMsg) ? (err.message || err.errMsg) : 'Request failed',
  }

  if (err && typeof err === 'object') {
    if (err.errMsg) error.errMsg = err.errMsg
    if (err.message) error.message = err.message
  }

  if (typeof responseData !== 'undefined') {
    error.data = responseData
  }

  if (response) {
    error.response = response
    if (typeof response.statusCode === 'number') {
      error.statusCode = response.statusCode
    }
  }

  return error
}

function refreshSession() {
  if (!auth.isRefreshTokenValid()) {
    return Promise.resolve(false)
  }

  if (!refreshPromise) {
    refreshPromise = new Promise((resolve, reject) => {
      const refreshToken = auth.getRefreshToken()
      if (!refreshToken) {
        resolve(false)
        return
      }

      wx.request({
        url: buildUrl('/auth/refresh'),
        method: 'POST',
        header: {
          'content-type': 'application/json',
        },
        data: {
          refresh_token: refreshToken,
        },
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            const normalized = auth.normalizeAuthTokenPayload(parseResponseData(res))
            auth.saveSession(normalized, undefined)
            resolve(true)
            return
          }
          resolve(false)
        },
        fail(err) {
          reject(err)
        },
        complete() {
          refreshPromise = null
        },
      })
    }).finally(() => {
      refreshPromise = null
    })
  }

  return refreshPromise
}

function request(options) {
  const method = String(options.method || 'GET').toUpperCase()
  const url = String(options.url || '')
  const isAuthEndpoint = url.includes('/auth/')
  const headers = Object.assign({}, options.header || {})
  const token = auth.getAccessToken()

  if (!headers['content-type'] && !headers['Content-Type']) {
    headers['content-type'] = method === 'GET' ? 'application/json' : 'application/json'
  }

  if (token && !isAuthEndpoint) {
    headers.Authorization = `Bearer ${token}`
  }

  let data = options.data
  if (method === 'POST' && headers['content-type'] === 'application/x-www-form-urlencoded' && data && typeof data === 'object') {
    data = serializeForm(data)
  }

  return new Promise((resolve, reject) => {
    const doRequest = (retried) => {
      wx.request({
        url: buildUrl(url),
        method,
        data,
        header: headers,
        timeout: options.timeout || 60000,
        success(res) {
          const responseData = parseResponseData(res)

          if (res.statusCode === 401 && !isAuthEndpoint && !retried) {
            refreshSession()
              .then((refreshed) => {
                if (refreshed) {
                  const newToken = auth.getAccessToken()
                  if (newToken) {
                    headers.Authorization = `Bearer ${newToken}`
                  }
                  doRequest(true)
                  return
                }
                auth.clearSession()
                reject({ statusCode: 401, data: responseData, response: res })
              })
              .catch((err) => {
                auth.clearSession()
                reject(err)
              })
            return
          }

          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ data: responseData, response: res })
            return
          }

          reject({ statusCode: res.statusCode, data: responseData, response: res })
        },
        fail(err) {
          reject(normalizeRequestError(err, undefined, undefined))
        },
      })
    }

    doRequest(false)
  })
}

function uploadFile(options) {
  const headers = Object.assign({}, options.header || {})
  const token = auth.getAccessToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    const doUpload = (retried) => {
      wx.uploadFile({
        url: buildUrl(options.url),
        filePath: options.filePath,
        name: options.name || 'file',
        formData: options.formData || {},
        header: headers,
        timeout: options.timeout || 60000,
        success(res) {
          let data = res.data
          if (typeof data === 'string') {
            try {
              data = JSON.parse(data)
            } catch (err) {
              // keep raw text
            }
          }

          if (res.statusCode === 401 && !retried) {
            refreshSession()
              .then((refreshed) => {
                if (refreshed) {
                  const newToken = auth.getAccessToken()
                  if (newToken) {
                    headers.Authorization = `Bearer ${newToken}`
                  }
                  doUpload(true)
                  return
                }
                auth.clearSession()
                reject({ statusCode: 401, data, response: res })
              })
              .catch((err) => {
                auth.clearSession()
                reject(err)
              })
            return
          }

          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ data, response: res })
            return
          }

          reject({ statusCode: res.statusCode, data, response: res })
        },
        fail(err) {
          reject(normalizeRequestError(err, undefined, undefined))
        },
      })
    }

    doUpload(false)
  })
}

module.exports = {
  buildUrl,
  refreshSession,
  request,
  uploadFile,
}
