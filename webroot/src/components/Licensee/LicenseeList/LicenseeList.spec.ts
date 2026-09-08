//
//  LicenseeList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/1/2025.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeList from '@components/Licensee/LicenseeList/LicenseeList.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { AppModes } from '@/app.config';
import store from '@store/index';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('LicenseeList component', async () => {
    afterEach(async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('user/setCurrentCompact', null);
        await store.dispatch('license/resetStoreSearch');
    });

    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeList).exists()).to.equal(true);
    });
    it('should successfully prepare search params including license scope', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;

        await component.$store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        await component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.SOCIAL_WORK }));
        await component.$store.dispatch('license/setStoreSearch', {
            homeState: 'co',
            licenseScope: 'multi-state',
        });

        const requestConfig = component.prepareSearchBody();

        expect(requestConfig).to.matchPattern({
            compact: CompactType.SOCIAL_WORK,
            homeState: 'co',
            licenseScope: 'multi-state',
            '...': '',
        });
    });
    it('should successfully display license scope in the search tag', async () => {
        const wrapper = await mountShallow(LicenseeList);
        const component = wrapper.vm;

        await component.$store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        await component.$store.dispatch('license/setStoreSearch', {
            firstName: 'Test',
            lastName: 'User',
            homeState: 'co',
            licenseScope: 'multi-state',
        });

        expect(component.searchDisplayLicenseScope).to.equal(
            `${component.$t('licensing.licenseScope')}: Multi state`
        );
        expect(component.searchDisplayAll).to.equal([
            'Test User',
            component.searchDisplayHomeState,
            component.searchDisplayLicenseScope,
        ].join(', '));
    });
});
