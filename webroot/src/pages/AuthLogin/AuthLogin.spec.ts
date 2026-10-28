//
//  AuthLogin.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/22/2026.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';
import { mountShallow } from '@tests/helpers/setup';
import AuthLogin from '@pages/AuthLogin/AuthLogin.vue';
import { AppModes } from '@/app.config';
import { AuthTypes, authStorage, AUTH_LOGIN_GOTO_COMPACT } from '@utils/auth';
import { CompactType } from '@utils/compactConfig';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import cognitoAuth, { CognitoAuthStep } from '@utils/cognitoAuth';

describe('AuthLogin page', async () => {
    const originalClientId = envConfig.cognitoClientIdStaff;
    const originalAuthDomain = envConfig.cognitoAuthDomainStaff;
    const originalLicenseeClientId = envConfig.cognitoClientIdLicensee;
    const originalLicenseeAuthDomain = envConfig.cognitoAuthDomainLicensee;

    afterEach(() => {
        envConfig.cognitoClientIdStaff = originalClientId;
        envConfig.cognitoAuthDomainStaff = originalAuthDomain;
        envConfig.cognitoClientIdLicensee = originalLicenseeClientId;
        envConfig.cognitoAuthDomainLicensee = originalLicenseeAuthDomain;
        authStorage.removeItem(AUTH_LOGIN_GOTO_COMPACT);
    });

    it('should mount the page component', async () => {
        const wrapper = await mountShallow(AuthLogin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AuthLogin).exists()).to.equal(true);
    });
    it('should show login fields for a supported staff compact', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        await nextTick();

        expect(wrapper.vm.isSupportedTarget).to.equal(true);
        expect(wrapper.vm.appMode).to.equal(AppModes.JCC);
        expect(wrapper.vm.authType).to.equal(AuthTypes.STAFF);
        expect(wrapper.vm.isLoginStep).to.equal(true);
        expect(wrapper.vm.title).to.equal(wrapper.vm.$t('auth.staffLoginTitle'));
        expect(wrapper.vm.compactLabel).to.equal('');
        expect(wrapper.find('.auth-compact').exists()).to.equal(false);
        expect(wrapper.vm.formData.email).to.not.equal(undefined);
        expect(wrapper.vm.formData.password).to.not.equal(undefined);
        const returnLink = wrapper.find('.auth-return-link');

        expect(returnLink.text()).to.equal(wrapper.vm.$t('auth.backToDashboard'));
        expect(returnLink.attributes('href')).to.equal('/Dashboard');
        expect(wrapper.find('img.auth-logo').attributes('alt')).to.equal(wrapper.vm.$t('common.appName'));
    });
    it('should name the selected compact above the staff login title', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';
        authStorage.setItem(AUTH_LOGIN_GOTO_COMPACT, CompactType.ASLP);

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        await nextTick();

        expect(wrapper.find('.auth-compact').text()).to.equal('Audiology and Speech Language Pathology (ASLP)');
        expect(wrapper.find('h1.auth-title').text()).to.equal(wrapper.vm.$t('auth.staffLoginTitle'));
    });
    it('should title a practitioner login separately from staff', async () => {
        envConfig.cognitoClientIdLicensee = 'licensee-client';
        envConfig.cognitoAuthDomainLicensee = 'https://licensee.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/licensee/jcc');
        wrapper.vm.applyRoute();
        await nextTick();

        expect(wrapper.vm.authType).to.equal(AuthTypes.LICENSEE);
        expect(wrapper.find('h1.auth-title').text()).to.equal(wrapper.vm.$t('auth.practitionerLoginTitle'));
    });
    it('should label the login button as logging in while the request is in progress', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        wrapper.vm.isFormLoading = true;

        expect(wrapper.vm.submitLabel).to.equal(wrapper.vm.$t('auth.loggingIn'));
    });
    it('should label the forgot-password button as sending code while the request is in progress', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc?step=forgot-password');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        wrapper.vm.isFormLoading = true;

        expect(wrapper.vm.submitLabel).to.equal(wrapper.vm.$t('auth.sendingCode'));
    });
    it('should label the MFA code button as verifying while the request is in progress', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.step = CognitoAuthStep.MFA_CODE;
        wrapper.vm.initFormInputs();
        wrapper.vm.isFormLoading = true;

        expect(wrapper.vm.submitLabel).to.equal(wrapper.vm.$t('auth.verifyingCode'));
    });
    it('should open forgot password from the query step', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc?step=forgot-password');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        await nextTick();

        expect(wrapper.vm.isForgotPasswordStep).to.equal(true);
        expect(wrapper.vm.formData.email).to.not.equal(undefined);
        expect(wrapper.vm.formData.password).to.equal(undefined);
    });
    it('should move to MFA setup after a successful password challenge', async () => {
        const signInStub = sinon.stub(cognitoAuth, 'signInWithPassword').resolves({
            step: CognitoAuthStep.MFA_SETUP,
            totpSecret: 'SECRETKEY',
            totpSetupUri: 'otpauth://totp/CompactConnect:user@example.com?secret=SECRETKEY',
            mfaSetupExpiresAt: Date.now() + (15 * 60 * 1000),
        });

        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        wrapper.vm.formData.email.value = 'user@example.com';
        wrapper.vm.formData.password.value = 'temporary-password';
        await wrapper.vm.handleSubmit();
        await flushPromises();

        expect(signInStub.calledOnce).to.equal(true);
        expect(wrapper.vm.isMfaSetupStep).to.equal(true);
        expect(wrapper.vm.totpSecret).to.equal('SECRETKEY');
        expect(wrapper.vm.qrCodeDataUrl).to.be.a('string').with.length.above(0);
        expect(wrapper.vm.remainingMs).to.be.above(14 * 60 * 1000);
    });
    it('should keep the email and focus the step title when opening forgot password', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        wrapper.vm.formData.email.value = 'user@example.com';

        const focus = sinon.spy(HTMLElement.prototype, 'focus');

        await wrapper.vm.showForgotPassword();

        const title = wrapper.find('h1.auth-title');

        expect(wrapper.vm.isForgotPasswordStep).to.equal(true);
        expect(wrapper.vm.formData.email.value).to.equal('user@example.com');
        expect(title.attributes('tabindex')).to.equal('-1');
        expect(focus.calledOn(title.element)).to.equal(true);
        expect(wrapper.vm.formData.email.isTouched).to.equal(false);
        expect(wrapper.vm.formData.email.errorMessage).to.equal('');
    });
    it('should show the required error only after forgot password is submitted empty', async () => {
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.initFormInputs();
        await wrapper.vm.showForgotPassword();
        await wrapper.vm.handleSubmit();

        expect(wrapper.vm.formData.email.isTouched).to.equal(true);
        expect(wrapper.vm.formData.email.errorMessage).to.equal(wrapper.vm.$t('inputErrors.required'));
    });
    it('should announce when the setup key is copied', async () => {
        const writeText = sinon.stub().resolves();
        const originalClipboard = navigator.clipboard;

        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: { writeText },
        });
        envConfig.cognitoClientIdStaff = 'staff-client';
        envConfig.cognitoAuthDomainStaff = 'https://staff.example.com';

        const wrapper = await mountShallow(AuthLogin);

        await wrapper.vm.$router.push('/auth/login/staff/jcc');
        wrapper.vm.applyRoute();
        wrapper.vm.step = CognitoAuthStep.MFA_SETUP;
        wrapper.vm.totpSecret = 'SECRETKEY';
        await nextTick();
        await wrapper.vm.copySetupKey();
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: originalClipboard,
        });

        expect(writeText.calledOnceWith('SECRETKEY')).to.equal(true);
        expect(wrapper.vm.copyStatus).to.equal(wrapper.vm.$t('auth.copiedKey'));
        expect(wrapper.find('[role="status"]').text()).to.equal(wrapper.vm.$t('auth.copiedKey'));
    });
});
