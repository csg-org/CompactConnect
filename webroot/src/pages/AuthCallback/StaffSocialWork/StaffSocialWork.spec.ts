//
//  StaffSocialWork.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StaffSocialWork from '@pages/AuthCallback/StaffSocialWork/StaffSocialWork.vue';

describe('StaffSocialWork page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StaffSocialWork);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StaffSocialWork).exists()).to.equal(true);
    });
});
