//
//  Logout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/29/2026.
//

import sinon from 'sinon';
import axios from 'axios';
import { mountShallow } from '@tests/helpers/setup';
import Logout from '@pages/Logout/Logout.vue';
import { authStorage, tokens, AuthTypes } from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Logout page', async () => {
    let logoutStub;
    let originalCognitoConfig;

    beforeEach(() => {
        // Prevent created() from running real logout (clears shared store / redirects)
        logoutStub = sinon.stub(Logout.methods, 'logout').resolves();

        originalCognitoConfig = {
            cognitoClientIdStaff: envConfig.cognitoClientIdStaff,
            cognitoAuthDomainStaff: envConfig.cognitoAuthDomainStaff,
        };
        envConfig.cognitoClientIdStaff = 'test-staff-client-id';
        envConfig.cognitoAuthDomainStaff = 'https://staff-auth.test.example.com';
    });

    afterEach(() => {
        logoutStub.restore();
        envConfig.cognitoClientIdStaff = originalCognitoConfig.cognitoClientIdStaff;
        envConfig.cognitoAuthDomainStaff = originalCognitoConfig.cognitoAuthDomainStaff;
        authStorage.removeItem(tokens.staff.REFRESH_TOKEN);
    });

    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Logout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Logout).exists()).to.equal(true);
        expect(logoutStub.calledOnce).to.equal(true);
    });

    it('should successfully revoke tokens before logoutRequest in logoutChecklist', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const revokeStub = sinon.stub(component, 'revokeTokens').resolves();
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        await component.logoutChecklist(false);

        expect(revokeStub.calledOnce).to.equal(true);
        expect(revokeStub.firstCall.args[0]).to.equal(AuthTypes.STAFF);
        expect(dispatchSpy.calledWith('user/logoutRequest', AuthTypes.STAFF)).to.equal(true);
        expect(revokeStub.calledBefore(
            dispatchSpy.withArgs('user/logoutRequest', AuthTypes.STAFF)
        )).to.equal(true);

        revokeStub.restore();
        dispatchSpy.restore();
    });

    it('should successfully revoke licensee tokens when logged in as licensee only', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const revokeStub = sinon.stub(component, 'revokeTokens').resolves();

        await component.logoutChecklist(true);

        expect(revokeStub.firstCall.args[0]).to.equal(AuthTypes.LICENSEE);

        revokeStub.restore();
    });

    it('should successfully swallow revoke errors and log to analytics', async () => {
        const wrapper = await mountShallow(Logout);
        const component = wrapper.vm;
        const axiosPostStub = sinon.stub(axios, 'post').rejects(new Error('network'));
        const logEventStub = sinon.stub(component.$analytics, 'logEvent').returns(undefined);
        let didThrow = false;

        authStorage.setItem(tokens.staff.REFRESH_TOKEN, 'staff-refresh-token');

        await component.revokeTokens(AuthTypes.STAFF).catch(() => {
            didThrow = true;
        });

        expect(didThrow).to.equal(false);
        expect(logEventStub.calledOnce).to.equal(true);
        expect(logEventStub.firstCall.args[0]).to.equal('cognito_token_revoke_failed'); // https://console.statsig.com/3KcYv8LC2YCc1vsTkVi3Fb/metrics/metrics_catalog/Cognito%20Token%20Revocation%20Failure/event_count_custom?unitType=overall
        expect(logEventStub.firstCall.args[1]).to.equal(1);
        expect(logEventStub.firstCall.args[2]).to.matchPattern({
            authType: AuthTypes.STAFF,
            appMode: component.appMode,
            appGroupMode: component.appGroupMode,
            errorName: 'Error',
            errorCode: undefined,
            httpStatus: undefined,
        });

        axiosPostStub.restore();
        logEventStub.restore();
    });
});
