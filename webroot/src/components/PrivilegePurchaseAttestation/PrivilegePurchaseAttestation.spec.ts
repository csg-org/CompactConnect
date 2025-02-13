//
//  PrivilegePurchaseAttestation.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/4/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivilegePurchaseAttestation from '@components/PrivilegePurchaseAttestation/PrivilegePurchaseAttestation.vue';

describe('PrivilegePurchaseAttestation page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivilegePurchaseAttestation);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivilegePurchaseAttestation).exists()).to.equal(true);
    });
});
