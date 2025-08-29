//
//  MfaResetConfirmLicensee.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/22/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MfaResetConfirmLicensee from '@pages/MfaResetConfirmLicensee/MfaResetConfirmLicensee.vue';

describe('MfaResetConfirmLicensee page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(MfaResetConfirmLicensee);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MfaResetConfirmLicensee).exists()).to.equal(true);
    });
});
