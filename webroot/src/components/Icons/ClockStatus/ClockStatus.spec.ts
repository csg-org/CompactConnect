//
//  ClockStatus.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/7/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ClockStatus from '@components/Icons/ClockStatus/ClockStatus.vue';

describe('ClockStatus component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ClockStatus);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ClockStatus).exists()).to.equal(true);
    });
});
