//
//  UserRow.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserRow from '@components/Users/UserRow/UserRow.vue';

describe('UserRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserRow);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserRow).exists()).to.equal(true);
    });
});
