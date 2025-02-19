//
//  LicenseIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/16/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';

describe('LicenseIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseIcon).exists()).to.equal(true);
    });
});
