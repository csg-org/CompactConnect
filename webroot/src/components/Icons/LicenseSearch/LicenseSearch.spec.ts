//
//  LicenseSearch.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseSearch from '@components/Icons/LicenseSearch/LicenseSearch.vue';

describe('LicenseSearch component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseSearch);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseSearch).exists()).to.equal(true);
    });
});
