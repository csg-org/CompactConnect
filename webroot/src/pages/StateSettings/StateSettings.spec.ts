//
//  StateSettings.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/20/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateSettings from '@pages/StateSettings/StateSettings.vue';

describe('StateSettings page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(StateSettings);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateSettings).exists()).to.equal(true);
    });
});
