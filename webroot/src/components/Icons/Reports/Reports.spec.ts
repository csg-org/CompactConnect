//
//  Reports.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/16/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Reports from '@components/Icons/Reports/Reports.vue';

describe('Reports component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Reports);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Reports).exists()).to.equal(true);
    });
});
