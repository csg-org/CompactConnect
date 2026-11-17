//
//  RegisterLicenseePsypact.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/16/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import sinon from 'sinon';
import { mountFull, mountShallow } from '@tests/helpers/setup';
import RegisterLicenseePsypact from '@pages/RegisterLicenseePsypact/RegisterLicenseePsypact.vue';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';

use(chaiMatchPattern);

const populateValidForm = (component): void => {
    component.formData.firstName.value = 'Test';
    component.formData.lastName.value = 'User';
    component.formData.email.value = 'test@example.com';
    component.formData.newPassword.value = 'Test-Password-123!';
    component.formData.confirmPassword.value = 'Test-Password-123!';
};

describe('RegisterLicenseePsypact page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(RegisterLicenseePsypact).exists()).to.equal(true);
    });
    it('should render the initial form inputs', async () => {
        const wrapper = await mountFull(RegisterLicenseePsypact);

        expect(wrapper.find('.register-licensee-psypact-title').text()).to.equal('Create an account');
        expect(wrapper.find('#first-name').exists()).to.equal(true);
        expect(wrapper.find('#last-name').exists()).to.equal(true);
        expect(wrapper.find('#email').exists()).to.equal(true);
        expect(wrapper.find('#new-password').exists()).to.equal(true);
        expect(wrapper.find('#confirm-password').exists()).to.equal(true);
        expect(wrapper.find('input#password').exists()).to.equal(true);
        expect(wrapper.find('.register-licensee-psypact-summary-container').exists()).to.equal(false);
    });
    it('should not proceed to confirmation when passwords do not match', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        populateValidForm(component);
        component.formData.confirmPassword.value = 'Different-Password-123!';
        await component.handleProceedToConfirmation();

        expect(component.isConfirmationScreen).to.equal(false);
        expect(component.formData.confirmPassword.isValid).to.equal(false);
        expect(component.formData.confirmPassword.errorMessage).to.equal('Passwords must match');
    });
    it('should not proceed to confirmation when the form is invalid', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        await component.handleProceedToConfirmation();

        expect(component.isConfirmationScreen).to.equal(false);
        expect(component.isFormValid).to.equal(false);
    });
    it('should proceed to a read-only confirmation without the password', async () => {
        const wrapper = await mountFull(RegisterLicenseePsypact);
        const component = wrapper.vm;

        populateValidForm(component);
        await component.handleProceedToConfirmation();
        await nextTick();

        expect(component.isConfirmationScreen).to.equal(true);
        expect(wrapper.find('.summary-first-name').text()).to.equal('Test');
        expect(wrapper.find('.summary-last-name').text()).to.equal('User');
        expect(wrapper.find('.summary-email').text()).to.equal('test@example.com');
        expect(wrapper.find('.register-licensee-psypact-summary-container').text()).to.not.contain('Test-Password-123!');
    });
    it('should return to the form from confirmation', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        populateValidForm(component);
        await component.handleProceedToConfirmation();
        await component.handleBackToForm();

        expect(component.isConfirmationScreen).to.equal(false);
        expect(component.formData.firstName.value).to.equal('Test');
    });
    it('should prepare request data from the form values', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        populateValidForm(component);

        expect(component.prepRequestData()).to.matchPattern({
            givenName: 'Test',
            familyName: 'User',
            email: 'test@example.com',
            password: 'Test-Password-123!',
        });
    });
    it('should submit the psypact registration request and show success', async () => {
        const wrapper = await mountFull(RegisterLicenseePsypact);
        const component = wrapper.vm;
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        populateValidForm(component);
        await component.handleSubmit();
        await nextTick();
        await flushPromises();

        expect(dispatchSpy.calledWith('user/createLicenseeAccountPsypactRequest', {
            data: {
                givenName: 'Test',
                familyName: 'User',
                email: 'test@example.com',
                password: 'Test-Password-123!',
            },
        })).to.equal(true);
        expect(component.isFormSuccessful).to.equal(true);
        expect(wrapper.find('.register-licensee-psypact-success-title').text())
            .to.equal('Thanks for creating an account.');
    });
    it('should show a final error when the extra field is filled', async () => {
        const wrapper = await mountFull(RegisterLicenseePsypact);
        const component = wrapper.vm;
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');
        const extraField = wrapper.find('input#password').element as HTMLInputElement;

        document.body.appendChild(wrapper.element);
        extraField.value = 'bot';
        populateValidForm(component);
        await component.handleSubmit();

        expect(component.isFinalError).to.equal(true);
        expect(component.isFormSuccessful).to.equal(false);
        expect(dispatchSpy.calledWith('user/createLicenseeAccountPsypactRequest')).to.equal(false);
    });
    it('should keep the form editable on a 400 error response', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        component.handleErrorResponse({ message: 'Invalid email', responseStatus: 400 });

        expect(component.isFinalError).to.equal(false);
        expect(component.submitErrorMessage).to.equal('Invalid email');
    });
    it('should show a final rate limit error on a 429 error response', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        component.handleErrorResponse({ responseStatus: 429 });

        expect(component.isFinalError).to.equal(true);
        expect(component.submitErrorMessage).to.equal(component.$t('serverErrors.rateLimit'));
    });
    it('should show a final error on other error responses', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        component.handleErrorResponse({ message: 'Server error', responseStatus: 500 });

        expect(component.isFinalError).to.equal(true);
        expect(component.submitErrorMessage).to.equal('Server error');
    });
    it('should reset the form', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        populateValidForm(component);
        component.isConfirmationScreen = true;
        component.resetForm();

        expect(component.formData.firstName.value).to.equal('');
        expect(component.formData.newPassword.value).to.equal('');
        expect(component.formData.confirmPassword.value).to.equal('');
        expect(component.isConfirmationScreen).to.equal(false);
    });
    it('should mock populate a valid form', async () => {
        const wrapper = await mountShallow(RegisterLicenseePsypact);
        const component = wrapper.vm;

        await component.mockPopulate();

        expect(component.isFormValid).to.equal(true);
    });
});
