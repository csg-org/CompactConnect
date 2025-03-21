//
//  PublicDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PublicDashboard from '@pages/PublicDashboard/PublicDashboard.vue';

describe('PublicDashboard page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PublicDashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PublicDashboard).exists()).to.equal(true);
    });
});
