//
//  CompactSelector.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/2/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CompactSelector from '@components/CompactSelector/CompactSelector.vue';

describe('CompactSelector component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CompactSelector);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactSelector).exists()).to.equal(true);
    });
});
