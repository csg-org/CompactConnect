//
//  InputCreditCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/1/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputCreditCard from '@components/Forms/InputCreditCard/InputCreditCard.vue';

describe('InputCreditCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputCreditCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputCreditCard).exists()).to.equal(true);
    });
});
