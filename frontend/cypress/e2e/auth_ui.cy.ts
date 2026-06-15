import { registerViaUi, loginViaUi, uniqueName } from './_helpers'

describe('Auth UI regression', () => {
  it('registers and logs in through the UI', () => {
    const username = uniqueName('ui_auth')
    const password = 'Password123!'

    registerViaUi(username, password)

    cy.window().then((win) => {
      expect(win.localStorage.getItem('token')).to.be.a('string').and.not.be.empty
      expect(win.localStorage.getItem('user')).to.be.a('string').and.not.be.empty
    })

    cy.window().then((win) => {
      win.localStorage.clear()
    })

    loginViaUi(username, password)

    cy.window().then((win) => {
      expect(win.localStorage.getItem('token')).to.be.a('string').and.not.be.empty
    })
  })
})
