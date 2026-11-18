//
//  CreditCardIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CreditCardIcon from '@components/Icons/CreditCardIcon/CreditCardIcon.vue';

describe('CreditCardIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CreditCardIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CreditCardIcon).exists()).to.equal(true);
    });
});
