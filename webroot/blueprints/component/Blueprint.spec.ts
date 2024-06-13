//
//  Blueprint.spec.ts
//  <the-app-name>
//
//  Created by InspiringApps on MM/DD/YYYY.
//  Copyright © 2024. <the-customer-name>. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Blueprint from '@components/SubPath/Blueprint/Blueprint.vue';

describe('Blueprint component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Blueprint);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Blueprint).exists()).to.equal(true);
    });
});
