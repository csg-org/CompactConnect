//
//  User.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/6/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import User from '@components/Icons/User/User.vue';

describe('User component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(User);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(User).exists()).to.equal(true);
    });
});
