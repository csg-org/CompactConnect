//
//  PrivacyPolicy.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/30/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PrivacyPolicy from '@pages/PrivacyPolicy/PrivacyPolicy.vue';

describe('PrivacyPolicy page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(PrivacyPolicy);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PrivacyPolicy).exists()).to.equal(true);
    });
});
