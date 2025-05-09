//
//  LicenseHome.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 4/23/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseHome from '@components/Icons/LicenseHome/LicenseHome.vue';

describe('LicenseHome component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseHome);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseHome).exists()).to.equal(true);
    });
});
