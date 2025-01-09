//
//  Purchase.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Purchase from '@components/Icons/Purchase/Purchase.vue';

describe('Purchase component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Purchase);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Purchase).exists()).to.equal(true);
    });
});
