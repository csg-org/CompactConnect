//
//  UserAccount.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserAccount from '@components/UserAccount/UserAccount.vue';

describe('UserAccount component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserAccount);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserAccount).exists()).to.equal(true);
    });
});
