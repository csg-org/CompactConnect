//
//  CloseX.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/19/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CloseX from '@components/Icons/CloseX/CloseX.vue';

describe('CloseX component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CloseX);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CloseX).exists()).to.equal(true);
    });
});
