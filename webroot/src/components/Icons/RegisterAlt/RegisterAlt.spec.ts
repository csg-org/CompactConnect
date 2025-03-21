//
//  RegisterAlt.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/7/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import RegisterAlt from '@components/Icons/RegisterAlt/RegisterAlt.vue';

describe('RegisterAlt component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(RegisterAlt);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RegisterAlt).exists()).to.equal(true);
    });
});
