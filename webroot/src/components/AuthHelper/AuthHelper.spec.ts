//
//  AuthHelper.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AuthHelper from '@components/AuthHelper/AuthHelper.vue';
import { CognitoAuthStep } from '@utils/cognitoAuth';

describe('AuthHelper component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AuthHelper);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AuthHelper).exists()).to.equal(true);
    });
    it('should explain authenticator setup on the MFA screen', async () => {
        const wrapper = await mountShallow(AuthHelper, {
            props: {
                screen: CognitoAuthStep.MFA_SETUP,
            },
        });
        const text = wrapper.text();

        expect(wrapper.find('.auth-helper').exists()).to.equal(true);
        expect(text).to.contain(wrapper.vm.$t('auth.helper.mfaSetupTitle'));
        expect(text).to.contain(wrapper.vm.$t('auth.helper.mfaStepScan'));
        expect(text).to.contain('15 minutes');
        expect(text).to.not.contain('temporary');
        expect(text).to.not.contain('3-minute');
        expect(wrapper.find('a[href*="google.android.apps.authenticator2"]').attributes('target')).to.equal('_blank');
    });
    it('should show the short instructions for password and code screens', async () => {
        const screens = [
            [CognitoAuthStep.NEW_PASSWORD, 'auth.newPasswordInstructions'],
            [CognitoAuthStep.MFA_CODE, 'auth.mfaCodeInstructions'],
            [CognitoAuthStep.FORGOT_PASSWORD, 'auth.forgotPasswordInstructions'],
            [CognitoAuthStep.FORGOT_PASSWORD_CONFIRM, 'auth.confirmForgotPasswordInstructions'],
        ];

        await screens.reduce(async (previous, [screen, key]) => {
            await previous;
            const wrapper = await mountShallow(AuthHelper, {
                props: { screen },
            });

            expect(wrapper.find('.auth-instructions').text()).to.equal(wrapper.vm.$t(key));
            expect(wrapper.find('.auth-helper').exists()).to.equal(false);
        }, Promise.resolve());
    });
    it('should stay empty on the login screen', async () => {
        const wrapper = await mountShallow(AuthHelper, {
            props: {
                screen: CognitoAuthStep.LOGIN,
            },
        });

        expect(wrapper.find('.auth-helper').exists()).to.equal(false);
        expect(wrapper.find('.auth-instructions').exists()).to.equal(false);
    });
});
