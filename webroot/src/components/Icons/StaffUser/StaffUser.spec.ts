//
//  StaffUser.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StaffUser from '@components/Icons/StaffUser/StaffUser.vue';

describe('StaffUser component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StaffUser);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StaffUser).exists()).to.equal(true);
    });
});
