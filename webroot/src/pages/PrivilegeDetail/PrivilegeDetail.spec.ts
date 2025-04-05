//
//  PrivilegeDetail.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/18/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeDetail from '@pages/PrivilegeDetail/PrivilegeDetail.vue';

describe('PrivilegeDetail page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegeDetail);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeDetail).exists()).to.equal(true);
    });
});
