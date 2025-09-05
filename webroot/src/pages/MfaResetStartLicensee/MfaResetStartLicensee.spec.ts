//
//  MfaResetStartLicensee.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/22/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MfaResetStartLicensee from '@pages/MfaResetStartLicensee/MfaResetStartLicensee.vue';

describe('MfaResetStartLicensee page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(MfaResetStartLicensee);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MfaResetStartLicensee).exists()).to.equal(true);
    });
});
