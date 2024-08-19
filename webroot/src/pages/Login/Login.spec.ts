//
//  Login.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Login from '@pages/Login/Login.vue';

describe('Login page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Login);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Login).exists()).to.equal(true);
    });
});
