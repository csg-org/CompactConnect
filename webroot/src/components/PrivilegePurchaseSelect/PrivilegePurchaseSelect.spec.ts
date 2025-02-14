//
//  PrivilegePurchaseSelect.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseSelect from '@components/PrivilegePurchaseSelect/PrivilegePurchaseSelect.vue';

describe('PrivilegePurchaseSelect page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseSelect);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseSelect).exists()).to.equal(true);
    });
});
