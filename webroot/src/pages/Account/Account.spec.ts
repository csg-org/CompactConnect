//
//  Account.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Account from '@pages/Account/Account.vue';

describe('Account page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Account);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Account).exists()).to.equal(true);
    });
});
