//
//  Settings.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Settings from '@components/Icons/Settings/Settings.vue';

describe('Settings component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Settings);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Settings).exists()).to.equal(true);
    });
});
