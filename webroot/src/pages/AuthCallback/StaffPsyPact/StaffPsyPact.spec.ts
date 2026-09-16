//
//  StaffPsyPact.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/16/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StaffPsyPact from '@pages/AuthCallback/StaffPsyPact/StaffPsyPact.vue';

describe('StaffPsyPact page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StaffPsyPact);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StaffPsyPact).exists()).to.equal(true);
    });
});
