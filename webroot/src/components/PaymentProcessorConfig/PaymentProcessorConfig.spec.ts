//
//  PaymentProcessorConfig.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PaymentProcessorConfig from '@components/PaymentProcessorConfig/PaymentProcessorConfig.vue';

describe('PaymentProcessorConfig component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PaymentProcessorConfig);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PaymentProcessorConfig).exists()).to.equal(true);
    });
});
