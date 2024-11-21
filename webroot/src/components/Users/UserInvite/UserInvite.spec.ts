//
//  UserInvite.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/11/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserInvite from '@components/Users/UserInvite/UserInvite.vue';

describe('UserInvite component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserInvite);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserInvite).exists()).to.equal(true);
    });
});
