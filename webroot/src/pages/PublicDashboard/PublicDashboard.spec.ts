//
//  PublicDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { mountFull, mountShallow } from '@tests/helpers/setup';
import PublicDashboard from '@pages/PublicDashboard/PublicDashboard.vue';
import { AppModes } from '@/app.config';
import { AuthTypes, getCognitoConfig, getHostedLoginUri } from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('PublicDashboard page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PublicDashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PublicDashboard).exists()).to.equal(true);
    });
    it('should use staff cognito config in app.config (jcc)', async () => {
        const cognitoConfig = getCognitoConfig(AppModes.JCC, AuthTypes.STAFF);

        expect(cognitoConfig.scopes).to.equal('email openid phone profile aws.cognito.signin.user.admin');
        expect(cognitoConfig.clientId).to.equal(envConfig.cognitoClientIdStaff);
        expect(cognitoConfig.authDomain).to.equal(envConfig.cognitoAuthDomainStaff);
    });
    it('should use staff cognito config in app.config (cosmetology)', async () => {
        const cognitoConfig = getCognitoConfig(AppModes.COSMETOLOGY, AuthTypes.STAFF);

        expect(cognitoConfig.scopes).to.equal('email openid phone profile aws.cognito.signin.user.admin');
        expect(cognitoConfig.clientId).to.equal(envConfig.cognitoClientIdStaffCosmo);
        expect(cognitoConfig.authDomain).to.equal(envConfig.cognitoAuthDomainStaffCosmo);
    });
    it('should use licensee cognito config in app.config (jcc)', async () => {
        const cognitoConfig = getCognitoConfig(AppModes.JCC, AuthTypes.LICENSEE);

        expect(cognitoConfig.scopes).to.equal('email openid phone profile aws.cognito.signin.user.admin');
        expect(cognitoConfig.clientId).to.equal(envConfig.cognitoClientIdLicensee);
        expect(cognitoConfig.authDomain).to.equal(envConfig.cognitoAuthDomainLicensee);
    });
    it('should use fallback cognito config in app.config', async () => {
        expect(getCognitoConfig()).to.matchPattern({
            scopes: '',
            clientId: '',
            authDomain: '',
        });
    });
    it('should use fallback idp path in app.config', async () => {
        expect(getHostedLoginUri(AuthTypes.LICENSEE)).to.contain('/login');
    });
    it('should get correct hosted login uri config for staff (jcc)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.staffLoginUri(AppModes.JCC);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Fstaff%2Fjcc');
    });
    it('should get correct hosted login uri config for staff (cosmetology)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.staffLoginUri(AppModes.COSMETOLOGY);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Fstaff%2Fcosmo');
    });
    it('should get correct hosted login uri config for staff (social work)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.staffLoginUri(AppModes.SOCIAL_WORK);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Fstaff%2Fsocialwork');
    });
    it('should successfully render one staff login link per enabled compact', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const compactLinks = wrapper.findAll('.staff-compacts .login-link');
        const enabledCompacts = component.$compactsEnabled;

        expect(enabledCompacts.length).to.be.above(0);
        expect(compactLinks.length).to.equal(enabledCompacts.length);
        compactLinks.forEach((compactLink, index) => {
            expect(compactLink.text()).to.equal(component.getCompactDisplay(enabledCompacts[index]));
        });
    });
    it('should get correct hosted login uri config for licensee (jcc)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(component.hostedLoginUriLicensee).to.contain('/login');
        expect(component.hostedLoginUriLicensee).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(component.hostedLoginUriLicensee).to.contain(`&state=${component.csrfState}`);
        expect(component.hostedLoginUriLicensee).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(component.hostedLoginUriLicensee).to.contain('&code_challenge_method=S256');
        expect(component.hostedLoginUriLicensee).to.contain('&response_type=code');
        expect(component.hostedLoginUriLicensee).to.contain('%2Fauth%2Fcallback%2Flicensee%2Fjcc');
    });
});
