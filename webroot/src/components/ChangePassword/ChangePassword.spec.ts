//
//  ChangePassword.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ChangePassword from '@components/ChangePassword/ChangePassword.vue';

describe('ChangePassword component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ChangePassword);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ChangePassword).exists()).to.equal(true);
    });
});
