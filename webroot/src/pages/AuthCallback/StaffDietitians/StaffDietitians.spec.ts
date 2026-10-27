//
//  StaffDietitians.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StaffDietitians from '@pages/AuthCallback/StaffDietitians/StaffDietitians.vue';

describe('StaffDietitians page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StaffDietitians);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StaffDietitians).exists()).to.equal(true);
    });
});
