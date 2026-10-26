//
//  router.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import guards from '@router/_guards';
import routes from '@router/routes';
import store from '@/store';
import { AppModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { AuthTypes, getAuthCallbackPath, getInAppLoginPath } from '@utils/auth';

use(chaiMatchPattern);

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
    it('should redirect in-app login to the public dashboard when custom auth is off', async () => {
        const wasCustomAuth = envConfig.isCustomAuth;

        envConfig.isCustomAuth = false;

        const result = await guards.customAuthGuard();

        envConfig.isCustomAuth = wasCustomAuth;

        expect(result).to.matchPattern({ name: 'DashboardPublic' });
    });
    it('should allow in-app login when custom auth is on and the user is logged out', async () => {
        const wasCustomAuth = envConfig.isCustomAuth;

        envConfig.isCustomAuth = true;
        await store.dispatch('user/logoutRequest', AuthTypes.STAFF);

        const result = await guards.customAuthGuard();

        envConfig.isCustomAuth = wasCustomAuth;

        expect(result).to.equal(true);
    });
    it('should send a logged-in user home when custom auth is on', async () => {
        const wasCustomAuth = envConfig.isCustomAuth;

        envConfig.isCustomAuth = true;
        await store.dispatch('user/loginSuccess');

        const result = await guards.customAuthGuard();

        envConfig.isCustomAuth = wasCustomAuth;

        expect(result).to.matchPattern({ name: 'Home' });
    });
});
describe('Router auth callback paths', () => {
    it('should successfully match getAuthCallbackPath for all auth callback routes', () => {
        const expectedPaths = [
            { name: 'AuthCallbackStaffJcc', path: getAuthCallbackPath(AppModes.JCC, AuthTypes.STAFF) },
            { name: 'AuthCallbackStaffCosmo', path: getAuthCallbackPath(AppModes.COSMETOLOGY, AuthTypes.STAFF) },
            { name: 'AuthCallbackStaffSocialWork', path: getAuthCallbackPath(AppModes.SOCIAL_WORK, AuthTypes.STAFF) },
            { name: 'AuthCallbackStaffPsyPact', path: getAuthCallbackPath(AppModes.PSYPACT, AuthTypes.STAFF) },
            { name: 'AuthCallbackLicenseeJcc', path: getAuthCallbackPath(AppModes.JCC, AuthTypes.LICENSEE) },
            { name: 'AuthCallbackLicenseePsyPact', path: getAuthCallbackPath(AppModes.PSYPACT, AuthTypes.LICENSEE) },
        ];

        expectedPaths.forEach(({ name, path }) => {
            const route = routes.find((routeConfig) => routeConfig.name === name);

            expect(route?.path).to.equal(path);
        });
    });
    it('should successfully match the in-app login route', () => {
        const route = routes.find((routeConfig) => routeConfig.name === 'AuthLogin');

        expect(route?.path).to.equal('/auth/login/:authType/:appMode');
        expect(route?.beforeEnter).to.equal(guards.customAuthGuard);
        expect(getInAppLoginPath(AppModes.JCC, AuthTypes.STAFF)).to.equal('/auth/login/staff/jcc');
        expect(getInAppLoginPath(AppModes.PSYPACT, AuthTypes.LICENSEE)).to.equal('/auth/login/licensee/psypact');
        expect(getInAppLoginPath(AppModes.COSMETOLOGY, AuthTypes.PUBLIC)).to.equal('');
    });
});
