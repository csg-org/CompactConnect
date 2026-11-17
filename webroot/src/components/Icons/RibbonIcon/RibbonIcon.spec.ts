//
//  RibbonIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import RibbonIcon from '@components/Icons/RibbonIcon/RibbonIcon.vue';

describe('RibbonIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(RibbonIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RibbonIcon).exists()).to.equal(true);
    });
});
