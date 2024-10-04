//
//  LicenseePrivilegeList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseePrivilegeList from '@components/LicenseePrivilegeList/LicenseePrivilegeList.vue';

describe('LicenseePrivilegeList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseePrivilegeList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseePrivilegeList).exists()).to.equal(true);
    });
});
