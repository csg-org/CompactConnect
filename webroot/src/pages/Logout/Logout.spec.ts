//
//  Logout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Logout from '@pages/Logout/Logout.vue';

describe('Logout page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Logout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Logout).exists()).to.equal(true);
    });
});
