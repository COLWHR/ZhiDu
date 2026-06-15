const config = require('./config')
const auth = require('./auth')

function buildSocketUrl(forumId) {
  const base = config.getWsBaseUrl()
  const token = auth.getAccessToken()
  const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${base}/forums/${forumId}/ws${tokenQuery}`
}

function connectForumSocket(forumId, handlers) {
  const socketTask = wx.connectSocket({
    url: buildSocketUrl(forumId),
  })

  socketTask.onOpen((event) => {
    if (handlers && handlers.onOpen) handlers.onOpen(event)
  })

  socketTask.onClose((event) => {
    if (handlers && handlers.onClose) handlers.onClose(event)
  })

  socketTask.onError((event) => {
    if (handlers && handlers.onError) handlers.onError(event)
  })

  socketTask.onMessage((event) => {
    let data = event.data
    if (typeof data === 'string') {
      try {
        data = JSON.parse(data)
      } catch (err) {
        // keep raw string
      }
    }
    if (handlers && handlers.onMessage) handlers.onMessage(data, event)
  })

  return socketTask
}

module.exports = {
  buildSocketUrl,
  connectForumSocket,
}
