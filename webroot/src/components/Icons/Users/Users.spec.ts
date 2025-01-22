//
//  Users.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Users from '@components/Icons/Users/Users.vue';

describe('Users component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Users);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Users).exists()).to.equal(true);
    });
});
