describe('End-to-end smoke', () => {
  const username = `smoke_${Date.now()}`
  const password = '123456'
  const topic = `Smoke Forum ${Date.now()}`
  let forumId: number
  let personaId: number
  let authToken: string

  it('logs in, creates a forum, opens the detail view, and sends a chat message', () => {
    cy.request({
      method: 'POST',
      url: 'http://127.0.0.1:8000/api/v1/auth/register',
      body: {
        username,
        password
      },
      failOnStatusCode: true
    })

    cy.visit('/auth/login')

    cy.get('input').filter(':visible').eq(0).clear().type(username)
    cy.get('input').filter(':visible').eq(1).clear().type(password)
    cy.get('button[type="submit"]').click()

    cy.url({ timeout: 20000 }).should('include', '/dashboard')

    cy.window().then((win) => {
      authToken = win.localStorage.getItem('token') || ''
      expect(authToken).to.be.a('string').and.not.be.empty

      return cy.request({
        method: 'POST',
        url: 'http://127.0.0.1:8000/api/v1/personas/',
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        body: {
          name: `Smoke Persona ${Date.now()}`,
          title: 'Smoke Persona',
          bio: 'Persona for the forum smoke test',
          theories: [],
          stance: 'Neutral',
          system_prompt: 'Be concise and deterministic.',
          is_public: false
        }
      }).then((personaResponse) => {
        personaId = personaResponse.body.id

        return cy.request({
          method: 'POST',
          url: 'http://127.0.0.1:8000/api/v1/forums/',
          headers: {
            Authorization: `Bearer ${authToken}`
          },
          body: {
            topic,
            participant_ids: [personaId],
            duration_minutes: 5
          }
        }).then((createResponse) => {
          forumId = createResponse.body.id

          return cy.request({
            method: 'POST',
            url: `http://127.0.0.1:8000/api/v1/forums/${forumId}/start`,
            headers: {
              Authorization: `Bearer ${authToken}`
            },
            body: {
              ablation_flags: {
                mock_llm: true,
                no_summary: true
              }
            }
          })
        })
      })
    })

    cy.then(() => {
      cy.visit('/dashboard')
      cy.contains(topic, { timeout: 20000 }).should('be.visible')
      cy.contains(topic).click()

      cy.url({ timeout: 20000 }).should('include', `/forums/${forumId}`)
      cy.contains(topic).should('be.visible')
      cy.get('.forum-header').should('be.visible')
      cy.get('.chat-input-area').should('be.visible')

      cy.intercept('POST', `/api/v1/forums/${forumId}/chat`).as('sendChat')

      cy.get('.chat-input-area input').first().type('Hello from smoke test{enter}')
      cy.wait('@sendChat').its('response.statusCode').should('eq', 202)

      cy.request({
        method: 'POST',
        url: `http://127.0.0.1:8000/api/v1/forums/${forumId}/stop`,
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        failOnStatusCode: false
      })

      cy.request({
        method: 'DELETE',
        url: `http://127.0.0.1:8000/api/v1/forums/${forumId}`,
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      })

      cy.request({
        method: 'DELETE',
        url: `http://127.0.0.1:8000/api/v1/personas/${personaId}`,
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      })
    })
  })
})
