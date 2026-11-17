//
//  ClipboardCheckIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ClipboardCheckIcon from '@components/Icons/ClipboardCheckIcon/ClipboardCheckIcon.vue';

describe('ClipboardCheckIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ClipboardCheckIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ClipboardCheckIcon).exists()).to.equal(true);
    });
});
