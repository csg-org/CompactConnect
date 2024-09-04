//
//  UserList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserList from '@components/Users/UserList/UserList.vue';

describe('UserList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserList).exists()).to.equal(true);
    });
});
