//
//  home.js
//  InspiringApps modules
//
//  Created by InspiringApps on 5/19/20.
//
import { axeConfig } from '../support/axe-config';

// https://docs.cypress.io/api/introduction/api.html
describe('Home page', () => {
    before(() => {
        cy.visit('/');
    });

    it('should pass accessibility tests', () => {
        cy.injectAxe();
        cy.configureAxe(axeConfig);
        cy.checkA11y('.home-container');
    });
});
