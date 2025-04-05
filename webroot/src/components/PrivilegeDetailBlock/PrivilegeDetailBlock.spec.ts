//
//  PrivilegeDetailBlock.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/19/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeDetailBlock from '@components/PrivilegeDetailBlock/PrivilegeDetailBlock.vue';

describe('PrivilegeDetailBlock component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegeDetailBlock);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeDetailBlock).exists()).to.equal(true);
    });
});
