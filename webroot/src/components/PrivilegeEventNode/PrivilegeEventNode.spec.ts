//
//  PrivilegeEventNode.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/21/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeEventNode from '@components/PrivilegeEventNode/PrivilegeEventNode.vue';

describe('PrivilegeEventNode component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegeEventNode);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeEventNode).exists()).to.equal(true);
    });
});
