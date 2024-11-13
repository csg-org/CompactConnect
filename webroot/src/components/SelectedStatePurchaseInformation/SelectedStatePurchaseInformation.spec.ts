//
//  SelectedStatePurchaseInformation.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import SelectedStatePurchaseInformation from '@components/SelectedStatePurchaseInformation/SelectedStatePurchaseInformation.vue';

describe('SelectedStatePurchaseInformation component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(SelectedStatePurchaseInformation);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(SelectedStatePurchaseInformation).exists()).to.equal(true);
    });
});
