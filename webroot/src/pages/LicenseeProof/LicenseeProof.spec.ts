//
//  LicenseeProof.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/2/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeProof from '@pages/LicenseeProof/LicenseeProof.vue';

describe('LicenseeProof page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseeProof);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeProof).exists()).to.equal(true);
    });
});
