//
//  PageContainer.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageContainer from '@components/Page/PageContainer/PageContainer.vue';

describe('PageContainer component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageContainer);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageContainer).exists()).to.equal(true);
    });
});
