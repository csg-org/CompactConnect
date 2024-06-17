//
//  RightCaretIcon.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/3/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';

describe('RightCaretIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(RightCaretIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RightCaretIcon).exists()).to.equal(true);
    });
});
