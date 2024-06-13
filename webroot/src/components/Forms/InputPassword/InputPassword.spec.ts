//
//  InputPassword.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

describe('InputPassword component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputPassword, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputPassword).exists()).to.equal(true);
    });
    it('should show the password visibility eye icon', async () => {
        const wrapper = await mountFull(InputPassword, {
            props: {
                formInput: new FormInput(),
                showEyeIcon: true,
            },
        });

        expect(wrapper.findComponent(HidePasswordEye).exists()).to.equal(true);
    });
    it('should toggle the password visibility', async () => {
        const wrapper = await mountFull(InputPassword, {
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
