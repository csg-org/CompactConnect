//
//  InputLabel.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/21/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputLabel from '@components/Forms/InputLabel/InputLabel.vue';

describe('InputLabel component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputLabel);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputLabel).exists()).to.equal(true);
    });
});
