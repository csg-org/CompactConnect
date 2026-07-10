//
//  mixins.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/24/2026.
//

import { mountShallow } from '@tests/helpers/setup';
import AuthCallbackHandlerMixin from '@pages/AuthCallback/_mixins/handler.mixin';
import { AppModes } from '@/app.config';
import { AuthTypes, AUTH_CSRF_STATE } from '@utils/auth';
import sessionStorage from '@store/session.storage';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('AuthCallbackHandler mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AuthCallbackHandlerMixin).exists()).to.equal(true);
    });
    it('should successfully get default query param values', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        expect(component.authorizationCode).to.equal('');
        expect(component.stateParam).to.equal('');
    });
    it('should successfully get custom query param values', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        component.$route.query.code = 'abc';
        component.$route.query.state = 'def';

        expect(component.authorizationCode).to.equal('abc');
        expect(component.stateParam).to.equal('def');
    });
    it('should successfully get tokens', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        await component.getTokens(AppModes.JCC, AuthTypes.STAFF, 'http://localhost', 'abc');

        expect(component.$router.options.history.state.replaced).to.equal(true);
    });
    it('should verify a matching csrf state param', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        sessionStorage.setItem(AUTH_CSRF_STATE, 'csrf-token-123');
        component.$route.query.state = 'csrf-token-123';

        expect(component.verifyCsrfState()).to.equal(true);
    });
    it('should reject a mismatched csrf state param', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        sessionStorage.setItem(AUTH_CSRF_STATE, 'csrf-token-123');
        component.$route.query.state = 'csrf-token-999';

        expect(component.verifyCsrfState()).to.equal(false);
    });
    it('should reject when no csrf state is stored', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        sessionStorage.removeItem(AUTH_CSRF_STATE);
        component.$route.query.state = 'csrf-token-123';

        expect(component.verifyCsrfState()).to.equal(false);
    });
    it('should consume (remove) the stored csrf state after verifying', async () => {
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;

        sessionStorage.setItem(AUTH_CSRF_STATE, 'csrf-token-123');
        component.$route.query.state = 'csrf-token-123';
        component.verifyCsrfState();

        expect(sessionStorage.getItem(AUTH_CSRF_STATE)).to.equal(null);
    });
});
