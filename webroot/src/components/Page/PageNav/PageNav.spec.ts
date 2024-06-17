//
//  PageNav.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageNav from '@components/Page/PageNav/PageNav.vue';
import PageMainNav from '@components/Page/PageMainNav/PageMainNav.vue';

describe('PageNav component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageNav);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageNav).exists()).to.equal(true);
    });

    it('should have the PageMainNav child component', async () => {
        const wrapper = await mountShallow(PageNav);

        expect(wrapper.findComponent(PageMainNav).exists()).to.equal(true);
    });
});
