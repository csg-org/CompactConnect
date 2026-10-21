//
//  PublicDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import { mountFull, mountShallow } from '@tests/helpers/setup';
import PublicDashboard from '@pages/PublicDashboard/PublicDashboard.vue';
import { AppModes } from '@/app.config';
import { AuthTypes, getCognitoConfig, getHostedLoginUri } from '@utils/auth';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import { CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import store from '@store/index';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';

use(chaiMatchPattern);

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
    it('should get correct hosted login uri config for staff (psypact)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.staffLoginUri(AppModes.PSYPACT);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Fstaff%2Fpsypact');
    });
    it('should successfully render compact list in alphabetical order', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const compactButtons = wrapper.findAll('.compact-list-button');
        const { compactList } = component;

        expect(compactList.length).to.be.above(0);
        expect(compactButtons.length).to.equal(compactList.length);
        compactButtons.forEach((compactButton, index) => {
            expect(compactButton.text()).to.equal(component.getCompactDisplay(compactList[index]));
        });
        expect(wrapper.find('.privilege-search').exists()).to.equal(false);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(false);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(false);
        expect(wrapper.find('h1#dashboard-step-heading').exists()).to.equal(true);
        expect(wrapper.find('ul.compact-list').exists()).to.equal(true);
        expect(wrapper.findAll('ul.compact-list li').length).to.equal(compactList.length);
    });
    it('should successfully show login options after compact selection', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await component.selectCompact(CompactType.COUNSELING);
        await nextTick();
        await flushPromises();

        expect(wrapper.find('.compact-list-card').exists()).to.equal(false);
        expect(wrapper.find('.compact-select-card').exists()).to.equal(true);
        expect(wrapper.find('.privilege-search').exists()).to.equal(true);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(true);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(true);
        expect(wrapper.findAll('.login-link.staff').length).to.equal(1);
        expect(wrapper.find('h1#dashboard-step-heading').exists()).to.equal(true);
        expect(wrapper.find('#practitioner-login-heading').exists()).to.equal(true);
        expect(wrapper.find('#staff-login-heading').exists()).to.equal(true);
        expect(wrapper.find('#practitioner-login').attributes('aria-labelledby'))
            .to.equal('practitioner-login-heading practitioner-login-text');
        expect(wrapper.find('#practitioner-login-text').text()).to.equal('Login');
        expect(wrapper.find('#staff-login').attributes('aria-labelledby'))
            .to.equal('staff-login-heading staff-login-text');
        expect(wrapper.find('#staff-login-text').text()).to.equal('Login');
        expect(wrapper.find('.privilege-search .login-link').attributes('aria-label'))
            .to.equal('Search, Public lookup');
    });
    it('should successfully hide practitioner login for social work', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await component.selectCompact(CompactType.SOCIAL_WORK);
        await nextTick();
        await flushPromises();

        expect(wrapper.find('.privilege-search').exists()).to.equal(true);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(false);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(true);
    });
    it('should successfully hide practitioner login for cosmetology', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await component.selectCompact(CompactType.COSMETOLOGY);
        await nextTick();
        await flushPromises();

        expect(wrapper.find('.privilege-search').exists()).to.equal(true);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(false);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(true);
    });
    it('should successfully update login options when compact selection changes', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await component.selectCompact(CompactType.COUNSELING);
        await nextTick();
        await flushPromises();

        expect(wrapper.find('.provider-login-card').exists()).to.equal(true);

        await component.selectCompact(CompactType.SOCIAL_WORK);
        await nextTick();
        await flushPromises();

        expect(wrapper.find('.provider-login-card').exists()).to.equal(false);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(true);
    });
    it('should successfully replace stale license search compact on compact selection', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        await store.dispatch('license/setStoreSearch', {
            compact: CompactType.ASLP,
            firstName: 'Test',
            lastName: '',
            state: '',
        });
        await component.selectCompact(CompactType.COUNSELING);
        await nextTick();
        await flushPromises();

        expect(store.state.user.currentCompact?.type).to.equal(CompactType.COUNSELING);
        expect(store.state.license.search.compact).to.equal(CompactType.COUNSELING);
        expect(store.state.license.search.firstName).to.equal('Test');

        await store.dispatch('license/resetStoreSearch');
    });
    it('should successfully move focus to the step heading after compact selection', async () => {
        const wrapper = await mountFull(PublicDashboard);
        const component = wrapper.vm;

        document.body.appendChild(wrapper.element);
        await component.selectCompact(CompactType.COUNSELING, true);
        await nextTick();
        await flushPromises();

        const heading = wrapper.find('#dashboard-step-heading');

        expect(heading.exists()).to.equal(true);
        expect(document.activeElement).to.equal(heading.element);
    });
    it('should successfully restore selected compact from the store', async () => {
        await store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: CompactType.COUNSELING }));

        const wrapper = await mountFull(PublicDashboard);

        await nextTick();
        await flushPromises();

        expect(wrapper.find('.compact-list-card').exists()).to.equal(false);
        expect(wrapper.find('.compact-select-card').exists()).to.equal(true);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(true);
        expect(wrapper.find('.staff-login-card').exists()).to.equal(true);
    });
    it('should successfully skip compact list and show login options (psypact)', async () => {
        await store.dispatch('setAppMode', AppModes.PSYPACT);

        const wrapper = await mountFull(PublicDashboard);

        await nextTick();
        await flushPromises();

        expect(wrapper.findAll('.compact-list-button').length).to.equal(0);
        expect(wrapper.find('.compact-select-card').exists()).to.equal(false);
        expect(wrapper.find('.privilege-search').exists()).to.equal(true);
        expect(wrapper.find('.provider-login-card').exists()).to.equal(true);
        expect(wrapper.findAll('.login-link.staff').length).to.equal(1);
    });
    it('should get correct hosted login uri config for licensee (jcc)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.licenseeLoginUri(AppModes.JCC);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Flicensee%2Fjcc');
    });
    it('should get correct hosted login uri config for licensee (psypact)', async () => {
        const wrapper = await mountShallow(PublicDashboard);
        const component = wrapper.vm;

        await nextTick();
        await flushPromises();

        const loginUri = component.licenseeLoginUri(AppModes.PSYPACT);

        expect(component.csrfState).to.be.a('string').with.length.above(0);
        expect(component.pkceChallenge).to.be.a('string').with.length.above(0);
        expect(loginUri).to.contain('/login');
        expect(loginUri).to.contain('scope=email%20openid%20phone%20profile%20aws.cognito.signin.user.admin');
        expect(loginUri).to.contain(`&state=${component.csrfState}`);
        expect(loginUri).to.contain(`&code_challenge=${component.pkceChallenge}`);
        expect(loginUri).to.contain('&code_challenge_method=S256');
        expect(loginUri).to.contain('&response_type=code');
        expect(loginUri).to.contain('%2Fauth%2Fcallback%2Flicensee%2Fpsypact');
    });
});
