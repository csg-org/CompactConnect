//
//  PageHeader.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageHeader from '@components/Page/PageHeader/PageHeader.vue';

describe('PageHeader component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageHeader);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageHeader).exists()).to.equal(true);
    });
});
