import {
  createForum,
  createPersona,
  deleteForum,
  deletePersona,
  getAuthToken,
  loginViaUi,
  registerUser,
  startForum,
  uniqueName
} from './_helpers'

describe('Upload, WebSocket, reconnect regression', () => {
  let token = ''
  let forumId = 0
  let personaId = 0

  afterEach(() => {
    if (forumId) {
      cy.request({
        method: 'DELETE',
        url: `http://127.0.0.1:8000/api/v1/forums/${forumId}`,
        headers: {
          Authorization: `Bearer ${token}`
        },
        failOnStatusCode: false
      })
    }

    forumId = 0

    if (personaId) {
      deletePersona(token, personaId)
    }

    personaId = 0
  })

  it('keeps the detail view live across reloads and handles uploads', () => {
    const username = uniqueName('ui_rt')
    const password = 'Password123!'
    const topic = uniqueName('Realtime Topic')

    registerUser(username, password)
    loginViaUi(username, password)

    getAuthToken()
      .then((value) => {
        token = value
        expect(token).to.be.a('string').and.not.be.empty
        return createPersona(token, uniqueName('Realtime Persona'))
      })
      .then((id) => {
        personaId = id
        return createForum(token, topic, [personaId])
      })
      .then((id) => {
        forumId = id
        return startForum(token, forumId)
      })
      .then(() => {
        cy.visit(`/forums/${forumId}`)
        cy.contains(topic, { timeout: 20000 }).should('be.visible')
        cy.get('.chat-input-area').should('be.visible')
        cy.wait(1500)

        const wsMessage1 = uniqueName('ws_msg_1')
        cy.request({
          method: 'POST',
          url: `http://127.0.0.1:8000/api/v1/forums/${forumId}/messages`,
          headers: {
            Authorization: `Bearer ${token}`
          },
          body: {
            forum_id: forumId,
            speaker_name: 'Smoke Bot',
            content: wsMessage1,
            turn_count: 1
          }
        })
        cy.contains(wsMessage1, { timeout: 20000 }).should('be.visible')

        cy.reload()
        cy.contains(wsMessage1, { timeout: 20000 }).should('be.visible')
        cy.wait(1500)

        const wsMessage2 = uniqueName('ws_msg_2')
        cy.request({
          method: 'POST',
          url: `http://127.0.0.1:8000/api/v1/forums/${forumId}/messages`,
          headers: {
            Authorization: `Bearer ${token}`
          },
          body: {
            forum_id: forumId,
            speaker_name: 'Smoke Bot',
            content: wsMessage2,
            turn_count: 2
          }
        })
        cy.contains(wsMessage2, { timeout: 20000 }).should('be.visible')

        cy.intercept('POST', '**/api/v1/upload/image').as('uploadImage')
        cy.intercept('POST', `**/api/v1/forums/${forumId}/chat`).as('uploadChat')

        const pngBase64 =
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6qf2kAAAAASUVORK5CYII='

        cy.get('.chat-input-area input[type="file"]')
          .selectFile(
            {
              contents: Cypress.Buffer.from(pngBase64, 'base64'),
              fileName: 'smoke.png',
              mimeType: 'image/png'
            },
            { force: true }
          )

        cy.wait('@uploadImage').its('response.statusCode').should('eq', 200)
        cy.wait('@uploadChat').its('response.statusCode').should('eq', 202)

        cy.then(() => deleteForum(token, forumId))
      })
  })
})
