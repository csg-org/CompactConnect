//
//  StaffCosmo.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StaffCosmo from '@pages/AuthCallback/StaffCosmo/StaffCosmo.vue';

describe('StaffCosmo page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StaffCosmo);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StaffCosmo).exists()).to.equal(true);
    });
});
