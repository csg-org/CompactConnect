//
//  CollapseCaretButton.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';

describe('CollapseCaretButton component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CollapseCaretButton);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CollapseCaretButton).exists()).to.equal(true);
    });
});
