//
//  LicensingListPublic.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicensingListPublic from '@pages/LicensingListPublic/LicensingListPublic.vue';

describe('LicensingListPublic page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicensingListPublic);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicensingListPublic).exists()).to.equal(true);
    });
});
