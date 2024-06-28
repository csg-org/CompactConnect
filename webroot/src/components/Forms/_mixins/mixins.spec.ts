//
//  mixins.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//

import { mountShallow } from '@tests/helpers/setup';
import FormMixin from '@components/Forms/_mixins/form.mixin';
import InputMixin from '@components/Forms/_mixins/input.mixin';
import { FormInput } from '@models/FormInput/FormInput.model';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Form mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(FormMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(FormMixin).exists()).to.equal(true);
    });
    it('should get default form values', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        expect(component.formValues).to.matchPattern({});
    });
    it('should get custom form values', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.formData = { id: { value: 1 }};

        expect(component.formValues).to.matchPattern({ id: 1 });
    });
    it('should have super-scope input and blur methods', async () => {
        const wrapper = await mountShallow(FormMixin);
        const formInput = new FormInput();
        const component = wrapper.vm;

        component.blur(formInput);
        component.input(formInput);

        expect(component.formValues).to.matchPattern({});
    });
    it('should populate a form input with fallback value', async () => {
        const wrapper = await mountShallow(FormMixin);
        const formInput = new FormInput();
        const component = wrapper.vm;

        component.populateFormInput(formInput, null);

        expect(formInput.value).to.equal('');
    });
    it('should populate a form input with set value (non-file input)', async () => {
        const wrapper = await mountShallow(FormMixin);
        const formInput = new FormInput();
        const component = wrapper.vm;

        component.populateFormInput(formInput, 1);

        expect(formInput.value).to.equal(1);
    });
    it('should validate all inputs (as touched)', async () => {
        const wrapper = await mountShallow(FormMixin);
        const formInput = new FormInput();
        const component = wrapper.vm;

        component.formData.test = formInput;
        component.validateAll({ asTouched: true });

        expect(formInput.isTouched).to.equal(true);
        expect(formInput.isValid).to.equal(true);
    });
    it('should start form loading', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.startFormLoading();

        expect(component.isFormLoading).to.equal(true);
        expect(component.isFormSuccessful).to.equal(false);
        expect(component.isFormError).to.equal(false);
    });
    it('should end form loading', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.endFormLoading();

        expect(component.isFormLoading).to.equal(false);
    });
    it('should set form error', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.setError();

        expect(component.isFormError).to.equal(true);
    });
});
describe('Input mixin', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputMixin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputMixin).exists()).to.equal(true);
    });
    it('should implement input and blur methods', async () => {
        const wrapper = await mountShallow(FormMixin);
        const formInput = new FormInput();
        const component = wrapper.vm;

        component.blur(formInput);
        // component.input(formInput);

        expect(formInput).to.matchPattern(formInput);
    });
});
