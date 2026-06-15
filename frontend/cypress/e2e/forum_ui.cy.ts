import {
  createPersona,
  deletePersona,
  getAuthToken,
  loginViaUi,
  registerUser,
  uniqueName
} from './_helpers'

describe('Forum UI regression', () => {
  let token = ''
  let personaId = 0
  let forumId = 0

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

    if (personaId) {
      cy.request({
        method: 'DELETE',
        url: `http://127.0.0.1:8000/api/v1/personas/${personaId}`,
        headers: {
          Authorization: `Bearer ${token}`
        },
        failOnStatusCode: false
      })
    }

    forumId = 0
    personaId = 0
  })

  it('creates, starts, sends, and deletes a forum via the UI', () => {
    const username = uniqueName('ui_forum')
    const password = 'Password123!'
    const personaName = uniqueName('ui_persona')
    const topic = uniqueName('Forum Topic')

    registerUser(username, password)
    loginViaUi(username, password)

    getAuthToken()
      .then((value) => {
        token = value
        expect(token).to.be.a('string').and.not.be.empty
        return createPersona(token, personaName)
      })
      .then((id) => {
        personaId = id

        cy.visit('/forums')
        cy.get('.create-btn').click()
        cy.get('.create-modal').should('be.visible')
        cy.get('.create-form input').first().clear().type(topic)
        cy.get('.form-select .ant-select-selector').click()
        cy.get('.ant-select-dropdown').should('be.visible')
        cy.contains('.ant-select-item-option-content', personaName, { timeout: 10000 }).click()
        cy.get('.form-input-number input').clear().type('5')

        cy.intercept('POST', '**/api/v1/forums/').as('createForum')
        cy.get('.confirm-btn').click()

        cy.wait('@createForum').then(({ response }) => {
          forumId = Number(response?.body?.id)
          expect(forumId).to.be.greaterThan(0)

          cy.contains(topic, { timeout: 20000 }).should('be.visible')
          cy.get('.forum-card').contains(topic).click()
          cy.url({ timeout: 20000 }).should('include', `/forums/${forumId}`)

          cy.contains('.header-right button', '开始论坛').click()
          cy.get('.chat-input-area').should('be.visible')

          const chatText = uniqueName('ui_chat')
          cy.intercept('POST', `**/api/v1/forums/${forumId}/chat`).as('sendChat')
          cy.get('.chat-input-area input').first().type(`${chatText}{enter}`)
          cy.wait('@sendChat').its('response.statusCode').should('eq', 202)
          cy.get('.chat-input-area input').first().should('have.value', '')

          cy.get('.header-right').contains('删除').click()
          cy.get('.ant-popconfirm-buttons .ant-btn-primary').click({ force: true })
          cy.url({ timeout: 20000 }).should('include', '/forums')

          cy.then(() => deletePersona(token, personaId))
        })
      })
  })
})
