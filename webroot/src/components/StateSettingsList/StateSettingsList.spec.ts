//
//  StateSettingsList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateSettingsList from '@components/StateSettingsList/StateSettingsList.vue';

describe('StateSettingsList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StateSettingsList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateSettingsList).exists()).to.equal(true);
    });
});
