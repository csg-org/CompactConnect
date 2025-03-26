//
//  Register.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Register from '@components/Icons/Register/Register.vue';

describe('Register component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Register);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Register).exists()).to.equal(true);
    });
});
