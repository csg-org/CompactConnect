//
//  CompactSettings.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CompactSettings from '@pages/CompactSettings/CompactSettings.vue';

describe('CompactSettings page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(CompactSettings);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactSettings).exists()).to.equal(true);
    });
});
