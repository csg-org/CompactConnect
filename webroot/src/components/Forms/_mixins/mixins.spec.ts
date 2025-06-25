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
import Joi from 'joi';

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
    it('should get custom form values (standard)', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.formData = { id: { value: 1 }};

        expect(component.formValues).to.matchPattern({ id: 1 });
    });
    it('should get custom form values (exclude disabled by default)', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.formData = {
            prop1: { value: 1 },
            prop2: { value: 2, isDisabled: true },
        };

        expect(component.formValues).to.matchPattern({ prop1: 1 });
    });
    it('should get custom form values (override to include disabled)', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;

        component.shouldValuesIncludeDisabled = true;
        component.formData = {
            prop1: { value: 1 },
            prop2: { value: 2, isDisabled: true },
        };

        expect(component.formValues).to.matchPattern({ prop1: 1, prop2: 2 });
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

        component.populateFormInput(formInput);

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
    it('should show invalid form error when there is an invalid input', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;
        const formInput = new FormInput();

        formInput.name = 'test-input';
        formInput.isValid = false;
        formInput.isSubmitInput = false;
        formInput.validation = Joi.string().required();
        component.formData.testInput = formInput;

        // Mock scrollToInput method to verify it gets called
        let scrollToInputCalled = false;

        component.scrollToInput = () => {
            scrollToInputCalled = true;
        };

        component.showInvalidFormError();

        expect(scrollToInputCalled).to.equal(true);
    });
    it('should not call scrollToInput when all inputs are valid', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;
        const formInput = new FormInput();

        formInput.name = 'test-input';
        formInput.isValid = true;
        formInput.isSubmitInput = false;
        component.formData.testInput = formInput;

        // Mock scrollToInput method to verify it doesn't get called
        let scrollToInputCalled = false;

        component.scrollToInput = () => {
            scrollToInputCalled = true;
        };

        component.showInvalidFormError();

        expect(scrollToInputCalled).to.equal(false);
    });
    it('should skip submit inputs when finding invalid form inputs', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;
        const submitInput = new FormInput();
        const regularInput = new FormInput();

        submitInput.name = 'submit-input';
        submitInput.isValid = false;
        submitInput.isSubmitInput = true;
        submitInput.validation = Joi.string().required();

        regularInput.name = 'regular-input';
        regularInput.isValid = false;
        regularInput.isSubmitInput = false;
        regularInput.validation = Joi.string().required();

        component.formData.submitInput = submitInput;
        component.formData.regularInput = regularInput;

        // Mock scrollToInput method to verify it gets called with the regular input
        let scrollToInputCalledWith = null;

        component.scrollToInput = (input) => {
            scrollToInputCalledWith = input;
        };

        component.showInvalidFormError();

        expect(scrollToInputCalledWith).to.not.be.null;
        expect((scrollToInputCalledWith as any).name).to.equal(regularInput.name);
    });
    it('should scroll to input element when element exists', async () => {
        const wrapper = await mountShallow(FormMixin);
        const component = wrapper.vm;
        const formInput = new FormInput();

        formInput.name = 'test-input';

        // Mock DOM element and its methods
        const mockElement = {
            scrollIntoView: () => { /* mock implementation */ },
            focus: () => { /* mock implementation */ }
        } as unknown as HTMLElement;

        // Mock document.getElementsByName
        const originalGetElementsByName = document.getElementsByName;

        document.getElementsByName = (name: string): NodeListOf<HTMLElement> => {
            if (name === 'test-input') {
                // Return a NodeList-like object with one element
                return {
                    length: 1,
                    0: mockElement,
                    item: (index: number) => (index === 0 ? mockElement : null),
                } as unknown as NodeListOf<HTMLElement>;
            }
            return {
                length: 0,
                item: () => null,
            } as unknown as NodeListOf<HTMLElement>;
        };

        let scrollIntoViewCalled = false;
        let focusCalled = false;

        (mockElement as any).scrollIntoView = () => {
            scrollIntoViewCalled = true;
        };
        (mockElement as any).focus = () => {
            focusCalled = true;
        };

        component.scrollToInput(formInput);

        expect(scrollIntoViewCalled).to.equal(true);
        expect(focusCalled).to.equal(true);

        // Restore original method
        document.getElementsByName = originalGetElementsByName;
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
        component.input(formInput);

        expect(formInput).to.matchPattern(formInput);
    });
});
