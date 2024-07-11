//
//  LicenseeList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeList from '@components/Licensee/LicenseeList/LicenseeList.vue';

describe('LicenseeList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeList).exists()).to.equal(true);
    });
});
