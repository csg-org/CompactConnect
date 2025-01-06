//
//  LicenseSearchAlt.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/2/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseSearchAlt from '@components/Icons/LicenseSearchAlt/LicenseSearchAlt.vue';

describe('LicenseSearchAlt component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseSearchAlt);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseSearchAlt).exists()).to.equal(true);
    });
});
