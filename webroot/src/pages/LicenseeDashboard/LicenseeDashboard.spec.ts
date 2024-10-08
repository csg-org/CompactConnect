//
//  LicenseeDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeDashboard from '@pages/LicenseeDashboard/LicenseeDashboard.vue';

describe('LicenseeDashboard page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseeDashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeDashboard).exists()).to.equal(true);
    });
});
