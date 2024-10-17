//
//  LicenseCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseCard from '@components/LicenseCard/LicenseCard.vue';

describe('LicenseCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseCard).exists()).to.equal(true);
    });
});
