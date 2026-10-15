//
//  LicenseePsyPact.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/16/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseePsyPact from '@pages/AuthCallback/LicenseePsyPact/LicenseePsyPact.vue';

describe('LicenseePsyPact page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseePsyPact);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseePsyPact).exists()).to.equal(true);
    });
});
