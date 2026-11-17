//
//  ShieldCheckIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ShieldCheckIcon from '@components/Icons/ShieldCheckIcon/ShieldCheckIcon.vue';

describe('ShieldCheckIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ShieldCheckIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ShieldCheckIcon).exists()).to.equal(true);
    });
});
