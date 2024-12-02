//
//  SelectedStatePurchaseInformation.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import SelectedStatePurchaseInformation from '@components/SelectedStatePurchaseInformation/SelectedStatePurchaseInformation.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';

describe('SelectedStatePurchaseInformation component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(SelectedStatePurchaseInformation, {
            props: {
                selectedStatePurchaseData: new PrivilegePurchaseOption(),
                jurisprudenceCheckInput: new FormInput()
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(SelectedStatePurchaseInformation).exists()).to.equal(true);
    });
});
