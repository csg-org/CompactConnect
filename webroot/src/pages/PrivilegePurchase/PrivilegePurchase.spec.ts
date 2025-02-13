//
//  PrivilegePurchase.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/31/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchase from '@pages/PrivilegePurchase/PrivilegePurchase.vue';

describe('PrivilegePurchase page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchase);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchase).exists()).to.equal(true);
    });
});
