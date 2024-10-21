//
//  UserRow.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserRow from '@components/Users/UserRow/UserRow.vue';
import { StaffUser } from '@models/StaffUser/StaffUser.model';

describe('UserRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserRow, {
            props: {
                listId: 'test',
                item: new StaffUser(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserRow).exists()).to.equal(true);
    });
});
