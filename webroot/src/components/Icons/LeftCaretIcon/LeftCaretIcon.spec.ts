//
//  LeftCaretIcon.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/3/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LeftCaretIcon from '@components/Icons/LeftCaretIcon/LeftCaretIcon.vue';

describe('LeftCaretIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LeftCaretIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LeftCaretIcon).exists()).to.equal(true);
    });
});
