//
//  PrivilegeHistory.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/26/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeHistory from '@components/PrivilegeHistory/PrivilegeHistory.vue';

describe('PrivilegeHistory component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegeHistory);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeHistory).exists()).to.equal(true);
    });
});
