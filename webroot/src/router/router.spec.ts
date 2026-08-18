//
//  router.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import guards from '@router/_guards';
import routes from '@router/routes';
import store from '@/store';
import { AppModes } from '@/app.config';
import { AuthTypes, getAuthCallbackPath } from '@utils/auth';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Router Guards', () => {
    it('should successfully return authentication guard', () => {
        // authGuard() has special handling for test-runner - expect `true` result here.
        const result = guards.authGuard();

        expect(result).to.equal(true);
    });
    it('should successfully return no-authentication guard (default)', async () => {
        await store.dispatch('user/logoutRequest', AuthTypes.STAFF);

        const result = guards.noAuthGuard();

        expect(result).to.equal(true);
    });
    it('should successfully return no-authentication guard (is logged in)', async () => {
        await store.dispatch('user/loginSuccess');

        const result = guards.noAuthGuard();

        expect(result).to.matchPattern({ name: 'Home' });
    });
});
describe('Router auth callback paths', () => {
    it('should successfully match getAuthCallbackPath for all auth callback routes', () => {
        const expectedPaths = [
            { name: 'AuthCallbackStaffJcc', path: getAuthCallbackPath(AppModes.JCC, AuthTypes.STAFF) },
            { name: 'AuthCallbackStaffCosmo', path: getAuthCallbackPath(AppModes.COSMETOLOGY, AuthTypes.STAFF) },
            { name: 'AuthCallbackStaffSocialWork', path: getAuthCallbackPath(AppModes.SOCIAL_WORK, AuthTypes.STAFF) },
            { name: 'AuthCallbackLicenseeJcc', path: getAuthCallbackPath(AppModes.JCC, AuthTypes.LICENSEE) },
        ];

        expectedPaths.forEach(({ name, path }) => {
            const route = routes.find((routeConfig) => routeConfig.name === name);

            expect(route?.path).to.equal(path);
        });
    });
});
