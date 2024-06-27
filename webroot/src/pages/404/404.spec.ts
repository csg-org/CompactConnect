//
//  404.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/7/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import page404 from '@pages/404/404.vue';

describe('404 page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(page404);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(page404).exists()).to.equal(true);
    });
});
