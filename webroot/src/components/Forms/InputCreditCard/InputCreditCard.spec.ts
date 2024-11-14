//
//  InputCreditCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/1/2024.
//

import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import InputCreditCard from '@components/Forms/InputCreditCard/InputCreditCard.vue';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputCreditCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputCreditCard);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputCreditCard).exists()).to.equal(true);
    });
    it('should toggle the credit card visibility', async () => {
        const wrapper = await mountFull(InputCreditCard, {
            props: {
                formInput: new FormInput(),
                showEyeIcon: true,
            },
        });
        const eyeIcon = wrapper.find('.eye-icon-container');
        const input = wrapper.find('input');

        await eyeIcon.trigger('click');
        expect(input.attributes().type).to.equal('text');
        expect(wrapper.findComponent(ShowPasswordEye).exists()).to.equal(true);

        await eyeIcon.trigger('click');
        expect(input.attributes().type).to.equal('password');
        expect(wrapper.findComponent(HidePasswordEye).exists()).to.equal(true);
    });
});
