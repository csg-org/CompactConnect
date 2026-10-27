//
//  LicenseeDietitians.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeDietitians from '@pages/AuthCallback/LicenseeDietitians/LicenseeDietitians.vue';

describe('LicenseeDietitians page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseeDietitians);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeDietitians).exists()).to.equal(true);
    });
});
