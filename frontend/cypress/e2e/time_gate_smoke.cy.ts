const apiRoot = 'http://127.0.0.1:8000/api/v1'

type TimeGateSession = {
  token: string
  user: {
    id: number
    username: string
    role: string
  }
  persona: {
    id: number
    name: string
  }
}

const createTimeGateSession = () => {
  const suffix = Date.now()
  const username = `timegate_${suffix}`
  const password = 'P@ssw0rd123!'
  const personaName = `\u65f6\u7a7a\u4e4b\u95e8\u6d4b\u8bd5_${suffix}`

  return cy
    .request({
      method: 'POST',
      url: `${apiRoot}/auth/register`,
      body: {
        username,
        password
      },
      failOnStatusCode: false
    })
    .then(() =>
      cy.request({
        method: 'POST',
        url: `${apiRoot}/auth/login`,
        form: true,
        body: {
          username,
          password
        }
      })
    )
    .then((loginResponse) => {
      const token = loginResponse.body.access_token as string

      return cy
        .request({
          method: 'GET',
          url: `${apiRoot}/users/me`,
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
        .then((userResponse) => {
          const user = userResponse.body as TimeGateSession['user']

          return cy
            .request({
              method: 'POST',
              url: `${apiRoot}/personas/`,
              headers: {
                Authorization: `Bearer ${token}`
              },
              body: {
                name: personaName,
                title: 'Smoke Persona',
                bio: 'Smoke persona for Time Gate e2e',
                theories: [],
                stance: 'Neutral',
                system_prompt:
                  '\u4f60\u662f\u4e00\u4e2a\u7b80\u6d01\u3001\u51c6\u786e\u3001\u7a33\u5b9a\u7684\u52a9\u624b\u3002\u8bf7\u4e25\u683c\u6309\u7167\u7528\u6237\u8981\u6c42\u56de\u7b54\u3002',
                is_public: false
              }
            })
            .then((personaResponse) => {
              const persona = personaResponse.body as TimeGateSession['persona']
              return {
                token,
                user,
                persona
              } as TimeGateSession
            })
        })
    })
}

const openTimeGate = (session: TimeGateSession) => {
  cy.visit('/time-gate', {
    onBeforeLoad(win) {
      win.localStorage.setItem('token', session.token)
      win.localStorage.setItem('user', JSON.stringify(session.user))
    }
  })

  cy.contains('\u6b22\u8fce\u6765\u5230\u65f6\u7a7a\u4e4b\u95e8', { timeout: 20000 }).should('be.visible')
  cy.contains('.agent-item', session.persona.name, { timeout: 20000 }).should('be.visible')
  cy.contains('.agent-item', session.persona.name).click()
  cy.get('.chat-input').should('be.visible')
}

const waitForAssistantReply = () => {
  cy.contains('.message-item.assistant .message-bubble', '\u8054\u901a', { timeout: 60000 }).should(
    'be.visible'
  )
}

describe('Time Gate smoke', () => {
  it('can clear the conversation and restore the welcome state', () => {
    createTimeGateSession().then((session) => {
      openTimeGate(session)

      cy.intercept('POST', '/api/v1/agents/chat/stream').as('streamReply')
      cy.get('.chat-input').type('\u53ea\u56de\u590d\u8054\u901a{enter}')
      cy.wait('@streamReply')
      waitForAssistantReply()

      cy.contains('\u6e05\u7a7a\u5bf9\u8bdd').click()
      cy.contains('.message-item.assistant .message-bubble', '\u4f60\u597d\uff0c\u6211\u662f').should(
        'be.visible'
      )
      cy.get('.messages-container .message-item').should('have.length', 1)
    })
  })

  it('can upload an image and send it with a normal chat message', () => {
    createTimeGateSession().then((session) => {
      openTimeGate(session)

      cy.intercept('POST', '/api/v1/agents/chat/stream').as('streamReply')

      cy.get('input[type="file"]').selectFile('cypress/fixtures/time-gate-smoke.svg', {
        force: true
      })

      cy.get('.chat-input')
        .invoke('val')
        .should((value) => {
          expect(String(value)).to.contain('![image](')
          expect(String(value)).to.contain('/uploads/')
        })

      cy.get('.chat-input').type('\u8bf7\u53ea\u56de\u590d\u8054\u901a{enter}')

      cy.wait('@streamReply').then(({ request }) => {
        const body =
          typeof request.body === 'string'
            ? (JSON.parse(request.body) as {
                context_messages?: Array<{ speaker?: string; role?: string; content?: string }>
              })
            : (request.body as {
                context_messages?: Array<{ speaker?: string; role?: string; content?: string }>
              })
        const lastMessage = body.context_messages?.[body.context_messages.length - 1]

        expect(lastMessage?.content || '').to.contain('![image](')
        expect(lastMessage?.content || '').to.contain('/uploads/')
      })

      waitForAssistantReply()
    })
  })
})
