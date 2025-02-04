//
//  PrivilegePurchaseInformationConfirmation.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/28/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseInformationConfirmation from '@pages/PrivilegePurchaseInformationConfirmation/PrivilegePurchaseInformationConfirmation.vue';

describe('PrivilegePurchaseInformationConfirmation page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseInformationConfirmation);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseInformationConfirmation).exists()).to.equal(true);
    });
});
