//
//  ClockIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ClockIcon from '@components/Icons/ClockIcon/ClockIcon.vue';

describe('ClockIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ClockIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ClockIcon).exists()).to.equal(true);
    });
});
