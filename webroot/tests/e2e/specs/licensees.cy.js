//
//  licensees.js
//  CompactConnect
//
//  Created by InspiringApps on 7/8/24.
//
import { axeConfig } from '../support/axe-config';

// https://docs.cypress.io/api/introduction/api.html
describe('Licensees page', () => {
    before(() => {
        cy.visit('/Licensing');
    });

    it('should pass accessibility tests', () => {
        cy.injectAxe();
        cy.configureAxe(axeConfig);
        cy.checkA11y('.licensing-list-section');
    });
});
