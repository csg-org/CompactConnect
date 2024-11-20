//
//  PurchaseSuccessful.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/5/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PurchaseSuccessful from '@pages/PurchaseSuccessful/PurchaseSuccessful.vue';

describe('PurchaseSuccessful page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PurchaseSuccessful);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PurchaseSuccessful).exists()).to.equal(true);
    });
});
