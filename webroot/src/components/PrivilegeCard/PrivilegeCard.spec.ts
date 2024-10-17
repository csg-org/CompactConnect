//
//  PrivilegeCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegeCard from '@components/PrivilegeCard/PrivilegeCard.vue';

describe('PrivilegeCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PrivilegeCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegeCard).exists()).to.equal(true);
    });
});
