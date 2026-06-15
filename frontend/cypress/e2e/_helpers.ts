export const apiBase = 'http://127.0.0.1:8000/api/v1'

export const uniqueName = (prefix: string) =>
  `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

export const registerUser = (username: string, password: string) => {
  return cy.request({
    method: 'POST',
    url: `${apiBase}/auth/register`,
    body: {
      username,
      password
    },
    failOnStatusCode: true
  })
}

export const loginViaUi = (username: string, password: string) => {
  cy.visit('/auth/login')
  cy.get('input').filter(':visible').eq(0).clear().type(username)
  cy.get('input').filter(':visible').eq(1).clear().type(password)
  cy.get('button[type="submit"]').click()
  cy.url({ timeout: 20000 }).should('include', '/dashboard')
}

export const registerViaUi = (username: string, password: string) => {
  cy.visit('/auth/register')
  cy.get('input').filter(':visible').eq(0).clear().type(username)
  cy.get('input').filter(':visible').eq(1).clear().type(password)
  cy.get('input').filter(':visible').eq(2).clear().type(password)
  cy.get('button[type="submit"]').click()
  cy.url({ timeout: 20000 }).should('include', '/dashboard')
}

export const getAuthToken = () => {
  return cy.window().then((win) => win.localStorage.getItem('token') || '')
}

export const createPersona = (token: string, name: string) => {
  return cy
    .request({
      method: 'POST',
      url: `${apiBase}/personas/`,
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: {
        name,
        title: 'Smoke Persona',
        bio: 'Smoke persona for Cypress regression tests',
        theories: [],
        stance: 'Neutral',
        system_prompt: 'Be concise and deterministic.',
        is_public: false
      }
    })
    .then((response) => response.body.id as number)
}

export const createForum = (token: string, topic: string, participantIds: number[] = []) => {
  return cy
    .request({
      method: 'POST',
      url: `${apiBase}/forums/`,
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: {
        topic,
        participant_ids: participantIds,
        duration_minutes: 5
      }
    })
    .then((response) => response.body.id as number)
}

export const startForum = (token: string, forumId: number) => {
  return cy.request({
    method: 'POST',
    url: `${apiBase}/forums/${forumId}/start`,
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: {}
  })
}

export const deleteForum = (token: string, forumId: number) => {
  return cy.request({
    method: 'DELETE',
    url: `${apiBase}/forums/${forumId}`,
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}

export const deletePersona = (token: string, personaId: number) => {
  return cy.request({
    method: 'DELETE',
    url: `${apiBase}/personas/${personaId}`,
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
}
