//
//  LicenseeJcc.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/24/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeJcc from '@pages/AuthCallback/LicenseeJcc/LicenseeJcc.vue';

describe('LicenseeJcc page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseeJcc);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeJcc).exists()).to.equal(true);
    });
});
