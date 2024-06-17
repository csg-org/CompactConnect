//
//  PageLoadingMask.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/19/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageLoadingMask from '@components/Page/PageLoadingMask/PageLoadingMask.vue';

describe('PageLoadingMask component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageLoadingMask);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageLoadingMask).exists()).to.equal(true);
    });
});
