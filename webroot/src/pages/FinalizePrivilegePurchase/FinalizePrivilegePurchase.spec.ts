//
//  FinalizePrivilegePurchase.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import FinalizePrivilegePurchase from '@pages/FinalizePrivilegePurchase/FinalizePrivilegePurchase.vue';

describe('FinalizePrivilegePurchase page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(FinalizePrivilegePurchase);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(FinalizePrivilegePurchase).exists()).to.equal(true);
    });
});
