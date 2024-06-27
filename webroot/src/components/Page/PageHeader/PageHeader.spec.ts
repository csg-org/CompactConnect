//
//  PageHeader.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageHeader from '@components/Page/PageHeader/PageHeader.vue';
import PageNav from '@components/Page/PageNav/PageNav.vue';

describe('PageHeader component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageHeader);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageHeader).exists()).to.equal(true);
    });
    it('should have the PageNav child component', async () => {
        const wrapper = await mountShallow(PageHeader);
        const nav = wrapper.findComponent(PageNav);

        expect(nav.exists()).to.equal(true);
    });
});
