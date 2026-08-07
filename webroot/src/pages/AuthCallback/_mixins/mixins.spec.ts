//
//  mixins.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/24/2026.
//

import sinon from 'sinon';
import axios from 'axios';
import { mountShallow } from '@tests/helpers/setup';
import AuthCallbackHandlerMixin from '@pages/AuthCallback/_mixins/handler.mixin';
import { AppModes } from '@/app.config';
import {
    AuthTypes,
    AUTH_CSRF_STATE,
    AUTH_PKCE_CODE_VERIFIER,
    authStorage,
    tokens
} from '@utils/auth';
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
        const cognitoAuthDomain = 'https://staff-auth.test.example.com';
        const cognitoClientId = 'test-staff-client-id';
        const tokenResponse = {
            access_token: 'access-token',
            id_token: 'id-token',
            token_type: 'Bearer',
        };
        const axiosPostStub = sinon.stub(axios, 'post').resolves({ data: tokenResponse });
        const wrapper = await mountShallow(AuthCallbackHandlerMixin);
        const component = wrapper.vm;
        const routerPushStub = sinon.stub(component.$router, 'push').resolves();
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        // created() fails CSRF and sets isError; reset for the direct getTokens call under test
        component.isError = false;
        component.$route.query.code = 'auth-code-123';
        sessionStorage.setItem(AUTH_PKCE_CODE_VERIFIER, 'pkce-verifier-123');

        await component.getTokens(AppModes.JCC, AuthTypes.STAFF, cognitoAuthDomain, cognitoClientId);

        expect(axiosPostStub.calledOnce).to.equal(true);
        expect(axiosPostStub.firstCall.args[0]).to.equal(`${cognitoAuthDomain}/oauth2/token`);
        expect(axiosPostStub.firstCall.args[1].get('grant_type')).to.equal('authorization_code');
        expect(axiosPostStub.firstCall.args[1].get('client_id')).to.equal(cognitoClientId);
        expect(axiosPostStub.firstCall.args[1].get('redirect_uri')).to.equal(
            `${component.$envConfig.domain}${component.$route.path}`
        );
        expect(axiosPostStub.firstCall.args[1].get('code')).to.equal('auth-code-123');
        expect(axiosPostStub.firstCall.args[1].get('code_verifier')).to.equal('pkce-verifier-123');
        expect(dispatchSpy.calledWith('user/updateAuthTokens', {
            tokenResponse,
            authType: AuthTypes.STAFF,
        })).to.equal(true);
        expect(dispatchSpy.calledWith('user/loginSuccess', AuthTypes.STAFF)).to.equal(true);
        expect(routerPushStub.calledWith({ name: 'Home' })).to.equal(true);
        expect(component.isError).to.equal(false);

        axiosPostStub.restore();
        routerPushStub.restore();
        dispatchSpy.restore();
        authStorage.removeItem(tokens.staff.AUTH_TOKEN);
        authStorage.removeItem(tokens.staff.AUTH_TOKEN_TYPE);
        authStorage.removeItem(tokens.staff.ID_TOKEN);
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
