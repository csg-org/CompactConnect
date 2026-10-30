//
//  MfaResetConfirmLicensee.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/22/2025.
//

import { expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import MfaResetConfirmLicensee from '@pages/MfaResetConfirmLicensee/MfaResetConfirmLicensee.vue';
import mockEnvConfig from '@tests/mocks/mockEnvConfig';
import { AppModes } from '@/app.config';
import { AuthTypes } from '@utils/auth';

describe('MfaResetConfirmLicensee page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(MfaResetConfirmLicensee);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MfaResetConfirmLicensee).exists()).to.equal(true);
    });
    it('should open in-app licensee login for the compact in the reset link', async () => {
        const wasCustomAuth = mockEnvConfig.isCustomAuth;
        const wasMockApi = mockEnvConfig.isUsingMockApi;
        const wrapper = await mountShallow(MfaResetConfirmLicensee);
        const replace = sinon.stub(wrapper.vm.$router, 'replace');

        mockEnvConfig.isCustomAuth = true;
        mockEnvConfig.isUsingMockApi = false;
        await wrapper.vm.$router.push({ path: '/MfaResetConfirm', query: { compact: 'psypact' }});
        wrapper.vm.goToLogin();

        expect(replace.calledOnce).to.equal(true);
        expect(replace.firstCall.args[0]).to.deep.equal({
            name: 'AuthLogin',
            params: {
                authType: AuthTypes.LICENSEE,
                appMode: AppModes.PSYPACT,
            },
        });

        mockEnvConfig.isCustomAuth = wasCustomAuth;
        mockEnvConfig.isUsingMockApi = wasMockApi;
    });
});
