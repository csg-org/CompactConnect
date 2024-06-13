//
//  ExampleMobileLinks.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/5/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleMobileLinks from '@components/StyleGuide/ExampleMobileLinks/ExampleMobileLinks.vue';

describe('ExampleMobileLinks component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleMobileLinks);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleMobileLinks).exists()).to.equal(true);
    });
});
