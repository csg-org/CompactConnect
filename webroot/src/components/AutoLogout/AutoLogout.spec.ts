//
//  AutoLogout.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/13/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AutoLogout from '@components/AutoLogout/AutoLogout.vue';

describe('AutoLogout component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AutoLogout);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AutoLogout).exists()).to.equal(true);
    });
});
