//
//  InputPassword.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2020.
//

import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { joiPasswordExtendCore } from 'joi-password';

const joiPassword = Joi.extend(joiPasswordExtendCore);

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
    it('should show password requirements', async () => {
        const { joiMessages } = (await mountShallow(MixinForm)).vm;
        const formInput = new FormInput({
            validation: joiPassword
                .string()
                .min(12)
                .minOfSpecialCharacters(1)
                .minOfLowercase(1)
                .minOfUppercase(1)
                .minOfNumeric(1)
                .doesNotInclude([
                    'password',
                ]),
        });
        const wrapper = await mountFull(InputPassword, {
            props: {
                formInput,
                joiMessages,
            },
        });
        const pwRequirements = wrapper.findAll('.password-requirement');

        expect(pwRequirements[0].text()).to.equal('Must be at least 12 characters');
        expect(pwRequirements[0].classes('is-valid')).to.equal(false);
        expect(pwRequirements[1].text()).to.equal('Must have at least 1 special character');
        expect(pwRequirements[1].classes('is-valid')).to.equal(false);
        expect(pwRequirements[2].text()).to.equal('Must have at least 1 lowercase character');
        expect(pwRequirements[2].classes('is-valid')).to.equal(false);
        expect(pwRequirements[3].text()).to.equal('Must have at least 1 uppercase character');
        expect(pwRequirements[3].classes('is-valid')).to.equal(false);
        expect(pwRequirements[4].text()).to.equal('Must have at least 1 number');
        expect(pwRequirements[4].classes('is-valid')).to.equal(false);
        expect(pwRequirements[5].text()).to.equal('Must not include your username or other common strings');
        expect(pwRequirements[5].classes('is-valid')).to.equal(false);
    });
});
