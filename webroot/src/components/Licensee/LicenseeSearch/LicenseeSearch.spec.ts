//
//  LicenseeSearch.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/12/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeSearch from '@components/Licensee/LicenseeSearch/LicenseeSearch.vue';

describe('LicenseeSearch component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeSearch);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeSearch).exists()).to.equal(true);
    });
});
