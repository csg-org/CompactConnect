//
//  MilitaryAffiliationInfoBlock.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/28/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MilitaryAffiliationInfoBlock from '@components/MilitaryAffiliationInfoBlock/MilitaryAffiliationInfoBlock.vue';

describe('MilitaryAffiliationInfoBlock component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(MilitaryAffiliationInfoBlock);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MilitaryAffiliationInfoBlock).exists()).to.equal(true);
    });
});
