//
//  PrivilegePurchaseSuccessful.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/5/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseSuccessful from '@components/PrivilegePurchaseSuccessful/PrivilegePurchaseSuccessful.vue';

describe('PrivilegePurchaseSuccessful page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseSuccessful);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseSuccessful).exists()).to.equal(true);
    });
});
