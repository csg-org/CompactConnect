//
//  CompactSettingsConfig.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CompactSettingsConfig from '@components/CompactSettingsConfig/CompactSettingsConfig.vue';

describe('CompactSettingsConfig component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CompactSettingsConfig);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactSettingsConfig).exists()).to.equal(true);
    });
});
