//
//  UpdateHomeJurisdiction.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UpdateHomeJurisdiction from '@components/UpdateHomeJurisdiction/UpdateHomeJurisdiction.vue';

describe('UpdateHomeJurisdiction component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(UpdateHomeJurisdiction);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UpdateHomeJurisdiction).exists()).to.equal(true);
    });
});
