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
import { Compact, CompactType } from '@models/Compact/Compact.model';

describe('LicensingDetail page', async () => {
    before(async () => {
        await mockStore.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));
    });
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicensingDetail);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicensingDetail).exists()).to.equal(true);
    });
});
