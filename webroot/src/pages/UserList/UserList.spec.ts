//
//  UserList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserList from '@pages/UserList/UserList.vue';

describe('UserList page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(UserList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserList).exists()).to.equal(true);
    });
});
