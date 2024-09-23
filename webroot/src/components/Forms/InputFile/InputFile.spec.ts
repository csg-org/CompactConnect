//
//  InputFile.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/8/2020.
//

import { nextTick } from 'vue';
import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

describe('InputFile component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputFile, {
            props: {
                formInput: new FormInput(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputFile).exists()).to.equal(true);
    });
    it('should successfully not trigger validation error when select is clicked', async () => {
        const wrapper = await mountShallow(InputFile, {
            props: {
                formInput: new FormInput({
                    validation: Joi.array().min(1),
                }),
            },
        });
        const component = wrapper.vm;
        const addFiles = wrapper.find('.add-files');

        await addFiles.trigger('click');

        expect(component.formInput.errorMessage).to.equal('');
        expect(wrapper.find('.form-field-error').exists()).to.equal(false);
    });
    it('should successfully trigger validation error if file selection cancelled', async () => {
        const wrapper = await mountShallow(InputFile, {
            props: {
                formInput: new FormInput({
                    validation: Joi.array().min(1),
                }),
            },
        });
        const component = wrapper.vm;

        await component.cancel(component.formInput);
        await nextTick();

        expect(component.formInput.errorMessage).to.equal('Required field');
        expect(wrapper.find('.form-field-error').exists()).to.equal(true);
    });
});
