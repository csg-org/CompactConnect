//
//  PrivilegePurchaseAcceptUI.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/29/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseAcceptUI from '@components/PrivilegePurchaseAcceptUI/PrivilegePurchaseAcceptUI.vue';

describe('PrivilegePurchaseAcceptUI component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseAcceptUI);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseAcceptUI).exists()).to.equal(true);
    });
});
