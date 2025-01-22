//
//  Dashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Dashboard from '@components/Icons/Dashboard/Dashboard.vue';

describe('Dashboard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Dashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Dashboard).exists()).to.equal(true);
    });
});
