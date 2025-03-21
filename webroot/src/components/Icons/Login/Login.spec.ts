//
//  Login.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Login from '@components/Icons/Login/Login.vue';

describe('Login component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Login);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Login).exists()).to.equal(true);
    });
});
