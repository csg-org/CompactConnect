//
//  FlagIcon.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/5/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import FlagIcon from '@components/Icons//FlagIcon/FlagIcon.vue';

describe('FlagIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(FlagIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(FlagIcon).exists()).to.equal(true);
    });
});
