//
//  Home.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Home from '@pages/Home/Home.vue';

describe('Home page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(Home);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Home).exists()).to.equal(true);
    });
});
