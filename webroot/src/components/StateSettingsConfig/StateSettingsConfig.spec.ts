//
//  StateSettingsConfig.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateSettingsConfig from '@components/StateSettingsConfig/StateSettingsConfig.vue';

describe('StateSettingsConfig component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StateSettingsConfig);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateSettingsConfig).exists()).to.equal(true);
    });
});
