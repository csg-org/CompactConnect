//
//  InputDate.spec.ts
//  <the-app-name>
//
//  Created by InspiringApps on 6/7/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { nextTick } from 'vue';

describe('InputDate component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputDate);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputDate).exists()).to.equal(true);
    });

    it('should validate against localValue instead of formInput.value', async () => {
        const wrapper = await mountShallow(InputDate, {
            props: {
                formInput: new FormInput({
                    id: 'test-date',
                    value: '2024-01-15', // Server format
                    validation: Joi.string().min(3),
                    isTouched: true,
                }),
            },
        });

        // Initialize
        await nextTick();
        const component = wrapper.vm as any;
        const { formInput } = wrapper.props();

        // Valid localValue should pass validation
        component.localValue = '01/15/2024';
        await nextTick();
        component.formInput.validate();

        expect(formInput.isValid).to.equal(true);
        expect(formInput.errorMessage).to.equal('');

        // localValue should fail validation
        component.localValue = '12';
        await nextTick();
        component.formInput.validate();

        expect(formInput.isValid).to.equal(false);
        expect(formInput.errorMessage).to.contain('must be at least 3 characters long');

        // Empty localValue should fail validation
        component.localValue = '';
        await nextTick();
        component.formInput.validate();

        expect(formInput.isValid).to.equal(false);
        expect(formInput.errorMessage).to.contain('is not allowed to be empty');

        // When formInput.value is set to empty string, watcher clears localValue
        // which causes validation to fail
        component.localValue = '01/15/2024';
        formInput.value = '';
        await nextTick();
        component.formInput.validate();

        expect(formInput.isValid).to.equal(false);
        expect(formInput.errorMessage).to.contain('is not allowed to be empty');
    });
});
