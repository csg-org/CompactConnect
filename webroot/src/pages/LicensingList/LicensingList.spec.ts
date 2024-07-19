//
//  LicensingList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicensingList from '@pages/LicensingList/LicensingList.vue';

describe('LicensingList page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicensingList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicensingList).exists()).to.equal(true);
    });
});
