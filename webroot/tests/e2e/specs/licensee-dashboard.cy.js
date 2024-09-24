//
//  licensee.js
//  CompactConnect
//
//  Created by InspiringApps on 7/16/24.
//
import { axeConfig } from '../support/axe-config';

// https://docs.cypress.io/api/introduction/api.html
describe('Licensee Dashboard page', () => {
    before(() => {
        cy.visit('/compact1/LicenseeDashboard');
    });

    it('should pass accessibility tests', () => {
        cy.injectAxe();
        cy.configureAxe(axeConfig);
        cy.checkA11y('.licensee-dashboard-container');
    });
});
