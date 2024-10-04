//
//  AdverseActionList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AdverseActionList from '@components/AdverseActionList/AdverseActionList.vue';

describe('AdverseActionList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AdverseActionList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AdverseActionList).exists()).to.equal(true);
    });
});
