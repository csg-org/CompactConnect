//
//  Logout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Logout from '@components/Icons/Logout/Logout.vue';

describe('Logout component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Logout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Logout).exists()).to.equal(true);
    });
});
