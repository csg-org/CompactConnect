//
//  PrivilegePurchaseLicense.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/3/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseLicense from '@components/PrivilegePurchaseLicense/PrivilegePurchaseLicense.vue';

describe('PrivilegePurchaseLicense component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseLicense);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseLicense).exists()).to.equal(true);
    });
});
