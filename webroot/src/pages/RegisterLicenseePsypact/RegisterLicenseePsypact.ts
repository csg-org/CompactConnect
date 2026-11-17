//
//  RegisterLicenseePsypact.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/16/2026.
//

import {
    Component,
    mixins,
    toNative,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import { passwordValidation } from '@utils/cognitoAuth';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import CheckCircle from '@components/Icons/CheckCircle/CheckCircle.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'RegisterLicenseePsypact',
    components: {
        Section,
        Card,
        InputText,
        InputPassword,
        InputSubmit,
        InputButton,
        CheckCircle,
        MockPopulate,
    }
})
class RegisterLicenseePsypact extends mixins(MixinForm) {
    //
    // Data
    //
    isFinalError = false;
    isConfirmationScreen = false;

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    mounted() {
        this.initExtraFields();
        this.initRecaptcha();
    }

    //
    // Computed
    //
    get submitErrorMessage(): string {
        return this.formSubmitInputs[0]?.errorMessage || '';
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    get elementTransitionMode(): string {
        // Test utils have a bug with transition modes; this only includes the mode in non-test contexts.
        return (this.$envConfig.isTest) ? '' : 'out-in';
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: computed(() => this.$t('common.firstName')),
                autocomplete: 'given-name',
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                autocomplete: 'family-name',
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            email: new FormInput({
                id: 'email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                autocomplete: 'email',
                validation: Joi.string().required().email({ tlds: false }).messages(this.joiMessages.string),
            }),
            newPassword: new FormInput({
                id: 'new-password',
                name: 'new-password',
                label: computed(() => this.$t('common.password')),
                autocomplete: 'new-password',
                validation: passwordValidation(this.joiMessages),
            }),
            confirmPassword: new FormInput({
                id: 'confirm-password',
                name: 'confirm-password',
                label: computed(() => this.$t('common.confirmPassword')),
                autocomplete: 'new-password',
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            handleSubmitInitial: new FormInput({
                isSubmitInput: true,
                id: 'submit-initial',
            }),
            handleSubmitConfirmation: new FormInput({
                isSubmitInput: true,
                id: 'submit-confirmation',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    initExtraFields(): void { // See Auth -> Registration section of README
        const passwordInput: HTMLElement = this.$refs.password as HTMLElement;

        if (passwordInput) {
            passwordInput.style.display = 'inline-block';
            passwordInput.style.height = '1px';
            passwordInput.style.width = '1px';
            passwordInput.style.overflow = 'hidden';
        }
    }

    initRecaptcha(): void {
        const recaptchaContainer: HTMLElement = this.$refs.recaptcha as HTMLElement;
        const scriptEl = document.createElement('script');
        const src = `https://www.google.com/recaptcha/api.js?render=${this.$envConfig.recaptchaKey}`;

        scriptEl.setAttribute('src', src);
        recaptchaContainer.appendChild(scriptEl);
    }

    validatePasswordMatch(): void {
        const confirmPasswordInput = this.formData.confirmPassword;
        const { newPassword, confirmPassword } = this.formValues;

        if (confirmPasswordInput && confirmPasswordInput.isTouched && newPassword !== confirmPassword) {
            confirmPasswordInput.errorMessage = this.$t('common.passwordsMustMatch');
            confirmPasswordInput.isValid = false;
            this.checkValidForAll();
        } else if (confirmPasswordInput && confirmPasswordInput.isTouched) {
            confirmPasswordInput.errorMessage = '';
            confirmPasswordInput.isValid = true;
            this.checkValidForAll();
        }
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.validatePasswordMatch();

        if (this.isFormValid) {
            this.startFormLoading();

            const password = document.getElementById('password') as HTMLInputElement;

            if (password?.value) {
                this.handleExtraFields();
            } else {
                const data = this.prepRequestData();

                await this.handleRecaptcha(data).catch(() => {
                    this.setError(this.$t('account.requestErrorRecaptcha'));
                });

                if (!this.isFormError) {
                    await this.$store.dispatch('user/createLicenseeAccountPsypactRequest', { data }).catch((err) => {
                        this.handleErrorResponse(err);
                    });
                }
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
            }

            this.endFormLoading();
        }
    }

    async handleProceedToConfirmation(): Promise<void> {
        this.validateAll({ asTouched: true });
        this.validatePasswordMatch();

        if (this.isFormValid) {
            this.isConfirmationScreen = true;

            // Wait for DOM to update, then scroll to confirmation screen
            await nextTick();

            this.scrollIntoView('summary-heading');
        }
    }

    scrollIntoView(elementId: string): void {
        const element = document.getElementById(elementId);

        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    async handleBackToForm(): Promise<void> {
        this.isConfirmationScreen = false;
        await nextTick();
        this.scrollIntoView('submit-initial');
    }

    handleExtraFields(): void {
        this.isFinalError = true;
        this.setError('');
        this.endFormLoading();
    }

    prepRequestData(): object {
        const {
            firstName,
            lastName,
            email,
            newPassword,
        } = this.formValues;

        return {
            givenName: firstName,
            familyName: lastName,
            email,
            password: newPassword,
        };
    }

    async handleRecaptcha(data): Promise<void> {
        const { recaptchaKey, isUsingMockApi } = this.$envConfig;

        if (!isUsingMockApi) {
            const { grecaptcha } = window as any; // From the SDK loaded in initRecaptcha() above
            const recaptchaToken = await new Promise((resolve, reject) => {
                grecaptcha.ready(() => {
                    grecaptcha.execute(recaptchaKey, { action: 'submit' }).then((token) => {
                        resolve(token);
                    }).catch((err) => {
                        reject(err);
                    });
                });
            }).catch((err) => { throw err; });

            data.token = recaptchaToken;
        }
    }

    handleErrorResponse(err): void {
        const { message = '', responseStatus } = err || {};

        switch (responseStatus) {
        case 400:
            // Form input error - show message inline and allow re-submit
            this.setError(message || this.$t('serverErrors.networkError'));
            break;
        case 429:
            // Rate limit error - break flow and show custom message
            this.isFinalError = true;
            this.setError(this.$t('serverErrors.rateLimit'));
            break;
        default:
            // All other errors - break flow and show server message if any
            this.isFinalError = true;
            this.setError(message);
            break;
        }

        this.endFormLoading();
    }

    resetForm(): void {
        this.formData.firstName.value = '';
        this.formData.lastName.value = '';
        this.formData.email.value = '';
        this.formData.newPassword.value = '';
        this.formData.confirmPassword.value = '';
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isConfirmationScreen = false;
        this.isFormError = false;
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    async mockPopulate(): Promise<void> {
        this.formData.firstName.value = 'Test';
        this.formData.lastName.value = 'User';
        this.formData.email.value = 'test@example.com';
        this.formData.newPassword.value = 'Test-Password-123!';
        this.formData.confirmPassword.value = 'Test-Password-123!';
        await nextTick();
        this.validateAll({ asTouched: true });
        this.validatePasswordMatch();
    }

    //
    // Watchers
    //
    @Watch('isFormError') isFormErrorChanged(): void {
        if (this.isFormError && !this.isFinalError) {
            this.handleBackToForm();
        }
    }

    @Watch('isConfirmationScreen') onConfirmationScreenChange(newValue: boolean): void {
        if (!newValue) { // Back to form
            this.$nextTick(() => {
                this.initExtraFields();
            });
        }
    }
}

export default toNative(RegisterLicenseePsypact);

// export default RegisterLicenseePsypact;
