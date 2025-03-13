//
//  SelectedLicenseInfo.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/7/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import SelectedLicenseInfo from '@components/SelectedLicenseInfo/SelectedLicenseInfo.vue';

describe('SelectedLicenseInfo component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(SelectedLicenseInfo);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(SelectedLicenseInfo).exists()).to.equal(true);
    });
});
