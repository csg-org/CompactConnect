//
//  Account.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Account from '@components/Icons/Account/Account.vue';

describe('Account component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Account);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Account).exists()).to.equal(true);
    });
});
