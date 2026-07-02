//
//  Globe.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Globe from '@components/Icons/Globe/Globe.vue';

describe('Globe component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Globe);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Globe).exists()).to.equal(true);
    });
});
