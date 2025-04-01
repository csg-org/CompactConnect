//
//  PublicPrivilegeDetail.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PublicPrivilegeDetail from '@pages/PublicPrivilegeDetail/PublicPrivilegeDetail.vue';

describe('PublicPrivilegeDetail page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PublicPrivilegeDetail);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PublicPrivilegeDetail).exists()).to.equal(true);
    });
});
