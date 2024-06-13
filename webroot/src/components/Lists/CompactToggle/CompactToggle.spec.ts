//
//  CompactToggle.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/10/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CompactToggle from '@components/Lists/CompactToggle/CompactToggle.vue';

describe('CompactToggle component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CompactToggle);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CompactToggle).exists()).to.equal(true);
    });
});
