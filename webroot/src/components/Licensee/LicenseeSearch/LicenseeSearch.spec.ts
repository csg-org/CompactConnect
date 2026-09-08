//
//  LicenseeSearch.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/1/2025.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeSearch from '@components/Licensee/LicenseeSearch/LicenseeSearch.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { AppModes } from '@/app.config';
import store from '@store/index';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('LicenseeSearch component', async () => {
    afterEach(async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('user/setCurrentCompact', null);
    });

    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeSearch);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeSearch).exists()).to.equal(true);
    });
    it('should successfully emit searchParams for social work staff search', async () => {
        await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        formData.homeState.value = 'co';
        formData.licenseScope.value = 'multi-state';
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            homeState: 'co',
            licenseScope: 'multi-state',
            '...': '',
        });
    });
    it('should successfully omit licenseScope from searchParams for social work public search', async () => {
        await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.SOCIAL_WORK }));

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                isPublicSearch: true,
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        formData.compact.value = CompactType.SOCIAL_WORK;
        formData.homeState.value = 'co';
        formData.licenseScope.value = 'multi-state';
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: CompactType.SOCIAL_WORK,
            homeState: 'co',
            licenseScope: undefined,
            '...': '',
        });
    });
    it('should successfully omit licenseScope from searchParams for cosmetology staff search', async () => {
        await store.dispatch('setAppMode', AppModes.COSMETOLOGY);

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        formData.homeState.value = 'co';
        formData.licenseScope.value = 'multi-state';
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            homeState: 'co',
            licenseScope: undefined,
            '...': '',
        });
    });
});
