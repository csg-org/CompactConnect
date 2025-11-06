//
//  InputSelectMultiple.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/2/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputSelectMultiple from '@components/Forms/InputSelectMultiple/InputSelectMultiple.vue';

describe('InputSelectMultiple component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputSelectMultiple);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputSelectMultiple).exists()).to.equal(true);
    });
});
