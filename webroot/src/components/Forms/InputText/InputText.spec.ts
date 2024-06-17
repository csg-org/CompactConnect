//
//  InputText.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/15/2020.
//

import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import InputText from '@components/Forms/InputText/InputText.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

describe('InputText component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputText, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputText).exists()).to.equal(true);
    });
    it('should validate the text input as correct', async () => {
        const wrapper = await mountFull(InputText, {
            props: {
                formInput: new FormInput({ value: 'abc' }),
            },
        });
        const { formInput } = wrapper.props();

        formInput.validate();

        expect(formInput.isValid).to.equal(true);
    });
    it('should validate the text input as incorrect, but not have error message', async () => {
        const wrapper = await mountFull(InputText, {
            props: {
                formInput: new FormInput({ value: 'abc', validation: Joi.string().min(4) }),
            },
        });
        const { formInput } = wrapper.props();

        formInput.validate();

        expect(formInput.isValid).to.equal(false);
        expect(formInput.errorMessage).to.equal('');
    });
    it('should validate the text input as incorrect, and have error message', async () => {
        const wrapper = await mountFull(InputText, {
            props: {
                formInput: new FormInput({ value: 'abc', validation: Joi.string().min(4), isTouched: true }),
            },
        });
        const { formInput } = wrapper.props();

        formInput.validate();

        expect(formInput.isValid).to.equal(false);
        expect(formInput.errorMessage).to.contain('must be at least 4 characters long');
    });
});
