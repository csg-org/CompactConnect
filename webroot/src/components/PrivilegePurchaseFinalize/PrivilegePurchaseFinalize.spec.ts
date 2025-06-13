//
//  PrivilegePurchaseFinalize.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseFinalize from '@components/PrivilegePurchaseFinalize/PrivilegePurchaseFinalize.vue';

describe('PrivilegePurchaseFinalize page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseFinalize);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseFinalize).exists()).to.equal(true);
    });
});
