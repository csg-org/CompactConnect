//
//  RegisterLicensee.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/14/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import { AppModes } from '@/app.config';
import RegisterLicensee from '@pages/RegisterLicensee/RegisterLicensee.vue';
import store from '@store/index';
import { flushPromises } from '@vue/test-utils';

describe('RegisterLicensee page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(RegisterLicensee);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RegisterLicensee).exists()).to.equal(true);
    });
    it('should redirect to the psypact registration page in psypact mode', async () => {
        await store.dispatch('setAppMode', AppModes.PSYPACT);

        const wrapper = await mountShallow(RegisterLicensee);

        await flushPromises();

        expect(wrapper.vm.$router.currentRoute.value.name).to.equal('RegisterLicenseePsypact');
        expect(wrapper.find('.register-licensee-card').exists()).to.equal(false);
    });
});
