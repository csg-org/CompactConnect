//
//  LicenseeDashboard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2024.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeDashboard from '@pages/LicenseeDashboard/LicenseeDashboard.vue';
import AuthorizationCard from '@components/AuthorizationCard/AuthorizationCard.vue';
import { AppModes } from '@/app.config';
import { ApplicationType } from '@models/Application/Application.model';
import store from '@store/index';

use(chaiMatchPattern);

describe('LicenseeDashboard page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(LicenseeDashboard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeDashboard).exists()).to.equal(true);
    });
    it('should always include an APIT and TAP authorization slot', async () => {
        const wrapper = await mountShallow(LicenseeDashboard);
        const component = wrapper.vm;

        expect(component.authorizationSlots).to.matchPattern([
            {
                type: ApplicationType.APIT,
                authorization: null,
            },
            {
                type: ApplicationType.TAP,
                authorization: null,
            },
        ]);
    });
    it('should not display authorization cards (jcc)', async () => {
        const wrapper = await mountShallow(LicenseeDashboard);

        expect(wrapper.findAllComponents(AuthorizationCard).length).to.equal(0);
    });
    it('should display authorization cards (psypact)', async () => {
        await store.dispatch('setAppMode', AppModes.PSYPACT);

        const wrapper = await mountShallow(LicenseeDashboard);

        expect(wrapper.findAllComponents(AuthorizationCard).length).to.equal(2);
    });
});
