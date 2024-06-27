//
//  commands.js
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

import 'cypress-file-upload';
import {
    appColors,
    getNumberOfPages
} from './utils';

// -- This is a parent command --
Cypress.Commands.add('login', () => {
    // Check if already logged in
    cy.getLocalStorage('auth_token').then((authToken) => {
        // If authToken doesn't exist yet, need to log in
        if (!authToken) {
            cy.setLocalStorage('auth_token', 'abc');
            cy.saveLocalStorage();
        }
    });
});

Cypress.Commands.add('getStore', () => {
    cy.window().its('app.$store');
});

Cypress.Commands.add('checkInputRadio', ($radioContainer, label, value) => {
    cy.wrap($radioContainer).within(() => {
        cy.get('[type="radio"]').should('be.visible').should('have.length', 1).should('have.value', value);
        cy.get('label').then(($label) => {
            cy.wrap($label)
                .should('be.visible')
                .should('have.length', 1)
                .should('have.css', 'color', appColors.primaryColor, 'cursor', 'pointer')
                .contains(label);

            const window = $label[0].ownerDocument.defaultView;
            const beforeEl = window.getComputedStyle($label[0], 'before');

            expect(beforeEl.getPropertyValue('content')).to.eq('" "');
            expect(beforeEl.getPropertyValue('border-color')).to.eq(appColors.lightGrey);
            expect(beforeEl.getPropertyValue('border-style')).to.eq('solid');
            expect(beforeEl.getPropertyValue('border-radius')).to.eq('50%');
        });
    });
});

Cypress.Commands.add('checkSortingOptions', (sortingOptions) => {
    // sortingOptions is an array of objects
    // (object of sortingOption.label and sortingOption.value)
    // with the names of the sorting options
    // on the left portion of the sorting bar
    cy.get('.sort-container').within(() => {
        cy.contains('Sort by:');
        cy.get('.sort-group').should('have.length', 2);
        cy.get('.sort-group').eq(0).within(() => {
            cy.get('.radio-container').should('have.length', sortingOptions.length);
            sortingOptions.forEach((sortOption, index) => {
                cy.get('.radio-container').eq(index).then(($radioContainer) => {
                    cy.checkInputRadio($radioContainer, sortOption.label, sortOption.value);
                });
            });
        });
        cy.get('.break').should('be.visible');
        cy.get('.sort-group').eq(1).within(() => {
            cy.get('.radio-container').should('have.length', 2);
            cy.get('.radio-container').eq(0).then(($radioContainer) => {
                cy.checkInputRadio($radioContainer, 'Ascending', 'asc');
            });
            cy.get('.radio-container').eq(1).then(($radioContainer) => {
                cy.checkInputRadio($radioContainer, 'Descending', 'desc');
            });
        });
    });
});

Cypress.Commands.add('checkPaginationBar', (numberOfPages, pageSize, position) => {
    if (numberOfPages > 0) {
        cy.get('.pagination-container').eq(position).within(() => {
            cy.get('.select-dropdown').should('have.value', pageSize.toString());
            cy.get('.pagination-item.page').should('have.length', numberOfPages);
            cy.get('.pagination-item.page').each(($el, index) => {
                const pageNum = index + 1;

                expect($el)
                    .to.contain(`${pageNum}`)
                    .to.have.class('clickable');
            });
        });
    }
});

Cypress.Commands.add('checkTopPaginationBar', (numberOfPages, pageSize) => {
    cy.checkPaginationBar(numberOfPages, pageSize, 0);
});

Cypress.Commands.add('checkBottomPaginationBar', (numberOfPages, pageSize) => {
    cy.checkPaginationBar(numberOfPages, pageSize, 1);
});

Cypress.Commands.add('checkPageSize', (pageNumber, pageSize, totalRecordsLength, recordContainerClass) => {
    cy.get('.pagination-item.page').eq(pageNumber - 1).should('have.class', 'selected').should('have.css', 'color', appColors.primaryColor);
    const numberOfPages = getNumberOfPages(totalRecordsLength, pageSize);
    const remainder = totalRecordsLength % pageSize;

    // // If it's last page and there is records remainder
    if (pageNumber === numberOfPages && remainder > 0) {
        cy.get(recordContainerClass).should('have.length', remainder);
    } else {
        cy.get(recordContainerClass).should('have.length', pageSize);
    }
});

Cypress.Commands.add('setPaginationSize', (paginationSizeOption) => {
    // paginationSizeOption can be equal to 5, 10, 20
    // Select page size from top pagination select
    cy.get('.pagination-container').eq(0).within(() => {
        cy.get('.select-dropdown').select(paginationSizeOption.toString());
    });
});

Cypress.Commands.add('checkPagination', (totalRecordsLength, paginationRowItem, topOnly) => {
    const paginationSizeOptions = [5, 10, 20];

    paginationSizeOptions.forEach((paginationSizeOption) => {
        const numberOfPages = getNumberOfPages(totalRecordsLength, paginationSizeOption);

        cy.setPaginationSize(paginationSizeOption);
        cy.checkTopPaginationBar(numberOfPages, paginationSizeOption);
        if (!topOnly) {
            cy.checkBottomPaginationBar(numberOfPages, paginationSizeOption);
        }
        for (let pageNumber = 1; pageNumber <= numberOfPages; pageNumber += 1) {
            // Change pages from top pagination select
            cy.get('.pagination-container').eq(0).within(() => {
                cy.get('.pagination-item.page').eq(pageNumber - 1).click();
            });
            cy.checkPageSize(pageNumber, paginationSizeOption, totalRecordsLength, paginationRowItem);
        }
    });
});

Cypress.Commands.add('checkSearch', () => {
    cy.viewport(1000, 660);
    // *
    // Has search bar that is typeable
    // *
    cy.wait(300);
    cy.get('.search-bar').within(() => {
        cy.get('img')
            .should('have.attr', 'src', '/img/ico-search.f9e8015a.svg')
            .should('have.attr', 'alt', 'Search Icon');
        cy.get('input').should('have.attr', 'placeholder', 'Search').type('a');
    });
});

Cypress.Commands.add('checkHeader', () => {
    cy.get('.page-header');
});

Cypress.Commands.add('checkFooter', () => {
    cy.get('.app-footer');
});

//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This is will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })
