//
//  InputNumber.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/31/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputNumber from '@components/Forms/InputNumber/InputNumber.vue';

describe('InputNumber component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputNumber);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputNumber).exists()).to.equal(true);
    });
});
