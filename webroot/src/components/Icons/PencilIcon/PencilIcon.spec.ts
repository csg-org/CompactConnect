//
//  PencilIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PencilIcon from '@components/Icons/PencilIcon/PencilIcon.vue';

describe('PencilIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PencilIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PencilIcon).exists()).to.equal(true);
    });
});
