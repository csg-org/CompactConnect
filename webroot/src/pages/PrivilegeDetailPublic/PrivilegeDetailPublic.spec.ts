//
//  PrivilegeDetailPublic.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeDetailPublic from '@pages/PrivilegeDetailPublic/PrivilegeDetailPublic.vue';

describe('PrivilegeDetailPublic page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegeDetailPublic);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeDetailPublic).exists()).to.equal(true);
    });
});
