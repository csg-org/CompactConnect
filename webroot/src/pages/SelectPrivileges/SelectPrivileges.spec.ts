//
//  SelectPrivileges.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import SelectPrivileges from '@pages/SelectPrivileges/SelectPrivileges.vue';

describe('SelectPrivileges page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(SelectPrivileges);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(SelectPrivileges).exists()).to.equal(true);
    });
});
