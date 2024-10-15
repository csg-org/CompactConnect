//
//  UserRowEdit.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UserRowEdit from '@components/Users/UserRowEdit/UserRowEdit.vue';
import { User } from '@models/User/User.model';

describe('UserRowEdit component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UserRowEdit, {
            props: {
                user: new User(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UserRowEdit).exists()).to.equal(true);
    });
});
