//
//  LicensingDetail.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import mockStore from '@tests/mocks/mockStore';
import LicensingDetail from '@pages/LicensingDetail/LicensingDetail.vue';

describe('LicensingDetail page', async () => {
    it('should mount the page component', async () => {
        mockStore.dispatch('user/setCurrentCompact', 'aslp');

        const wrapper = await mountShallow(LicensingDetail);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicensingDetail).exists()).to.equal(true);
    });
});
