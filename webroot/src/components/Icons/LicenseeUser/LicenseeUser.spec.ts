//
//  LicenseeUser.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeUser from '@components/Icons/LicenseeUser/LicenseeUser.vue';

describe('LicenseeUser component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeUser);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeUser).exists()).to.equal(true);
    });
});
