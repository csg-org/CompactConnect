//
//  PublicLicensingDetail.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/17/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PublicLicensingDetail from '@pages/PublicLicensingDetail/PublicLicensingDetail.vue';

describe('PublicLicensingDetail page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PublicLicensingDetail);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PublicLicensingDetail).exists()).to.equal(true);
    });
});
