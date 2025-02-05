//
//  RegisterLicensee.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/14/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import RegisterLicensee from '@pages/RegisterLicensee/RegisterLicensee.vue';

describe('RegisterLicensee page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(RegisterLicensee);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RegisterLicensee).exists()).to.equal(true);
    });
});
