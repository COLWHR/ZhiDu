describe('Skill repository', () => {
  it('shows SkillHub skills after login', () => {
    const username = `skillui_${Date.now()}`
    const password = 'password123'

    cy.request('POST', 'http://127.0.0.1:8000/api/v1/auth/register', {
      username,
      password
    })

    cy.request({
      method: 'POST',
      url: 'http://127.0.0.1:8000/api/v1/auth/login',
      form: true,
      body: {
        username,
        password
      }
    }).then(({ body }) => {
      window.localStorage.setItem('token', body.access_token)
      window.localStorage.setItem('refresh_token', body.refresh_token)
      window.localStorage.setItem('token_expires_at', body.access_token_expires_at)
      window.localStorage.setItem('refresh_token_expires_at', body.refresh_token_expires_at)
      window.localStorage.setItem('user', JSON.stringify({ id: 1, username, role: 'user' }))
    })

    cy.visit('/assistants/skills')

    cy.contains('Skill 仓库').should('be.visible')
    cy.contains('skillhub.web-tools-guide', { timeout: 15000 }).should('be.visible')
    cy.get('.skill-card').should('have.length.greaterThan', 10)
  })
})
