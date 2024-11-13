//
//  StateUpload.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2024.
//

import { nextTick } from 'vue';
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import StateUpload from '@components/StateUpload/StateUpload.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';

describe('StateUpload component', async () => {
    before(() => {
        global.requestAnimationFrame = (cb) => cb(); // JSDOM omits this global method, so we need to mock it ourselves
    });
    it('should mount the component', async () => {
        const wrapper = await mountShallow(StateUpload);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(StateUpload).exists()).to.equal(true);
    });
    it('should successfully show form success', async () => {
        const wrapper = await mountShallow(StateUpload);
        const component = wrapper.vm;

        component.$store.dispatch('user/setStoreUser', new StaffUser());
        component.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));
        component.isFormSuccessful = true;
        await nextTick();

        const success = wrapper.find('.state-upload-success');
        const reset = wrapper.find('.success-btn');

        expect(success.exists()).to.equal(true);
        expect(reset.exists()).to.equal(true);
    });
    it('should successfully reset form when user is done', async () => {
        const wrapper = await mountShallow(StateUpload);
        const component = wrapper.vm;

        component.isFormSuccessful = true;
        await nextTick();

        const reset = wrapper.find('.success-btn');

        await reset.trigger('click');

        const success = wrapper.find('.state-upload-success');
        const form = wrapper.find('.state-upload-form');

        expect(success.exists()).to.equal(false);
        expect(form.exists()).to.equal(true);
    });
});
