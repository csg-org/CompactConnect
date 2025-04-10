//
//  StatusTimeBlock.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/21/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StatusTimeBlock from '@components/StatusTimeBlock/StatusTimeBlock.vue';

describe('StatusTimeBlock component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StatusTimeBlock);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StatusTimeBlock).exists()).to.equal(true);
    });
});
