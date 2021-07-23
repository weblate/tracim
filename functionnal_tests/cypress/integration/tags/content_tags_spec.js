import { PAGES } from '../../support/urls_commands'
import { SELECTORS } from '../../support/generic_selector_commands'

describe('Create tags', () => {
  const fileTitle = 'FileForSwitch'
  const fullFilename = 'Linux-Free-PNG.png'
  const contentType = 'image/png'

  const tagCreatedByWorkspace = 'Tag from workspace'

  const flashMessageClass = '.flashmessage__container__content__text__paragraph'
  const flashMessageTextWorkspace = 'Your tag has been created'
  const flashMessageTextContent = 'Your tag has been added'

  const inputClass = '[data-cy=add_tag]'
  const itemListClass = '[data-cy=tag_list] li'
  const validateButtonClass = '[data-cy=validate_tag]'

  before(() => {
    cy.resetDB()
    cy.setupBaseDB()
  })

  describe('Tags', () => {
    for (const testedContent of ['file', 'note']) {
      describe(`in a ${testedContent}`, () => {
        beforeEach(() => {
          cy.resetDB()
          cy.setupBaseDB()
          cy.loginAs('administrators')
          cy.fixture('baseWorkspace').as('workspace').then(({ workspace_id: workspaceId }) => {
            cy.visitPage({ pageName: PAGES.DASHBOARD, params: { workspaceId } })
            cy.contains('.userstatus__role__text', 'Space manager')
            cy.getTag({ selectorName: SELECTORS.WORKSPACE_DASHBOARD })
              .find('.dashboard__workspace__detail__buttons .iconbutton')
              .click()
            cy.get('[data-cy=popin_right_part_tag').click()

            cy.get(inputClass).type(tagCreatedByWorkspace)
            cy.get(validateButtonClass).click()
            cy.contains(flashMessageClass, flashMessageTextWorkspace)
            if (testedContent === 'file') {
              cy.createFile(fullFilename, contentType, fileTitle, workspaceId).then(({ content_id: contentId }) => {
                cy.visitPage({
                  pageName: PAGES.CONTENT_OPEN,
                  params: { workspaceId, contentType: 'file', contentId }
                })
              })
              cy.get('[data-cy=popin_right_part_tag]').click()
            } else {
              cy.createHtmlDocument('A note', workspaceId).then(({ content_id: contentId }) => {
                cy.visitPage({
                  pageName: PAGES.CONTENT_OPEN,
                  params: { workspaceId, contentType: 'html-document', contentId }
                })
                cy.waitForTinyMCELoaded()
                cy.typeInTinyMCE('Bar')
                cy.get('[data-cy=editionmode__button__submit]').click()
                cy.get('[data-cy=popin_right_part_tag]').click()
              })
            }
          })
        })

        afterEach(function () {
          cy.cancelXHR()
        })

        it('should create and add two tags', () => {
          cy.get(inputClass).type('TagOne')
          cy.contains(validateButtonClass, 'Create and add')
          cy.get(validateButtonClass).click()
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.get(itemListClass).should('have.length', 1)
          cy.get(inputClass).type('TagTwo')
          cy.get(validateButtonClass).click()
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.get(itemListClass).should('have.length', 2)
        })

        it('should list the tags', () => {
          cy.get(inputClass).type('TagOne')
          cy.get(validateButtonClass).click()
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.get(itemListClass).should('have.length', 1)
          cy.get(inputClass).type('TagTwo')
          cy.get(validateButtonClass).click()
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.get(itemListClass).should('have.length', 2)
          // switch tab and come back
          cy.get('[data-cy=popin_right_part_timeline]').click()
          cy.get('[data-cy=popin_right_part_tag]').click()
          cy.get(itemListClass).should('have.length', 2)
          cy.get('[data-cy=tag_list]').first().should('contain', 'TagTwo')
        })

        it('should validate with Enter key', () => {
          cy.get(inputClass).type('TagOne').type('{enter}')
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.contains(itemListClass, 'TagOne')
        })

        it('should hide autocomplete with Esc key', () => {
          cy.get(inputClass).type('Ta')
          cy.get('.autocomplete').should('be.visible')
          cy.get(inputClass).type('{esc}')
          cy.get('.autocomplete').should('be.not.visible')
        })

        it('should add a tag that exists already in workspace', () => {
          cy.get(inputClass).type(tagCreatedByWorkspace).type('{esc}')
          cy.contains(validateButtonClass, 'Add')
          cy.get(validateButtonClass).click()
          cy.contains(flashMessageClass, flashMessageTextContent)
          cy.contains(itemListClass, tagCreatedByWorkspace)
        })
      })
    }
  })
})
