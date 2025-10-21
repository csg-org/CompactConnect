//
//  RegisterLicensee.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/14/2025.
//

import {
    Component,
    mixins,
    toNative,
    Watch
} from 'vue-facing-decorator';
import {
    reactive,
    computed,
    ComputedRef,
    nextTick
} from 'vue';
import { stateList, dateFormatPatterns } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Section from '@components/Section/Section.vue';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import CheckCircle from '@components/Icons/CheckCircle/CheckCircle.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import {
    formatDateInput,
    serverFormatToDateInput
} from '@models/_formatters/date';

interface SelectOption {
    value: string | number;
    name: string | ComputedRef<string>;
    isDisabled?: boolean;
}

@Component({
    name: 'RegisterLicensee',
    components: {
        Section,
        Card,
        InputText,
        InputDate,
        InputSelect,
        InputSubmit,
        InputButton,
        CheckCircle,
        MockPopulate,
    }
})
class RegisterLicensee extends mixins(MixinForm) {
    //
    // Data
    //
    compacts: Array<Compact> = [];
    selectedCompactStates: Array<State> = [];
    isFinalError = false;
    isConfirmationScreen = false;

    //
    // Lifecycle
    //
    async created() {
        this.initFormInputs();
        await this.getCompactStates();
    }

    mounted() {
        this.initExtraFields();
        this.initRecaptcha();
    }

    //
    // Computed
    //
    get licenseTypeOptions(): Array<SelectOption> {
        const options = [{ value: '', name: `- ${this.$t('common.select')} -`, isDisabled: true }];
        const licenseTypes = this.$tm('licensing.licenseTypes') || [];

        licenseTypes.forEach((licenseType) => {
            options.push({
                value: licenseType.key,
                name: licenseType.name,
                isDisabled: false,
            });
        });

        return options;
    }

    get stateOptions(): Array<SelectOption> {
        const { selectedCompactStates } = this;
        const options = [{ value: '', name: `- ${this.$t('common.select')} -`, isDisabled: true }];

        stateList?.forEach((state) => {
            const stateObject = new State({ abbrev: state });
            const value = stateObject?.abbrev?.toLowerCase();
            let name = stateObject?.name();
            let isDisabled = false;

            if (name && value) {
                const compactLiveState = selectedCompactStates.find((liveState) =>
                    liveState.abbrev?.toLowerCase() === value);

                if (!compactLiveState) {
                    name += ` (${this.$t('common.notLive')})`;
                    isDisabled = true;
                }

                options.push({ value, name, isDisabled });
            }
        });

        return options;
    }

    get submitLabel(): string {
        let label = this.$t('account.requestAccount');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

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

    get selectedState(): State | null {
        const selectedOption = this.stateOptions.find((option) => option.value === this.formData.licenseState.value);

        return (selectedOption && typeof selectedOption.value === 'string')
            ? new State({ abbrev: selectedOption.value.toUpperCase() })
            : null;
    }

    get formattedDob(): string {
        let formattedDob = '';
        const dobValue = this.formData.dob.value as string;

        if (dobValue) {
            const numericDate = serverFormatToDateInput(dobValue);

            formattedDob = formatDateInput(numericDate);
        }

        return formattedDob;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            licenseType: new FormInput({
                id: 'license-type',
                name: 'license-type',
                label: computed(() => this.$t('licensing.licenseType')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.licenseTypeOptions,
            }),
            licenseState: new FormInput({
                id: 'license-state',
                name: 'license-state',
                label: computed(() => this.$t('licensing.stateOfHomeLicense')),
                labelInfo: computed(() => this.$t('account.requestAccountHomeStateInfo')),
                autocomplete: 'address-level1',
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.stateOptions,
                isDisabled: true,
            }),
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
            ssnLastFour: new FormInput({
                id: 'ssn-last-four',
                name: 'ssn-last-four',
                label: computed(() => this.$t('licensing.ssnLastFour')),
                validation: Joi.string().length(4).required().messages(this.joiMessages.string),
            }),
            dob: new FormInput({
                id: 'dob',
                name: 'dob',
                label: computed(() => this.$t('common.dateOfBirth')),
                placeholder: computed(() => 'MM/DD/YYYY'),
                autocomplete: 'bday',
                validation: Joi.string()
                    .required()
                    .pattern(dateFormatPatterns.MM_DD_YYYY)
                    .messages(this.joiMessages.dateWithFormat('MM/DD/YYYY')),
            }),
            email: new FormInput({
                id: 'email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                autocomplete: 'email',
                validation: Joi.string().required().email({ tlds: false }).messages(this.joiMessages.string),
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

    async getCompactStates(): Promise<void> {
        await this.$store.dispatch('user/getCompactStatesForRegistrationRequest').then((response) => {
            this.compacts = response;
        }).catch((err) => {
            this.setError(`${this.$t('serverErrors.compactStatesLive')}: ${err?.message || ''}`);
            this.isFinalError = true;
        });
    }

    populateStatesInput(): void {
        const licenseTypes = this.$tm('licensing.licenseTypes') || [];
        const selectedLicenseType = this.formData.licenseType.value;
        const licenseTypeConfig = licenseTypes.find((config) => config.key === selectedLicenseType);
        const compactType = licenseTypeConfig?.compactKey;
        const selectedCompact = this.compacts.find((compact) => compact.type === compactType);
        const stateInput = this.formData.licenseState;

        if (selectedCompact?.memberStates) {
            this.selectedCompactStates = selectedCompact.memberStates;
            stateInput.valueOptions = this.stateOptions;
            stateInput.isDisabled = false;
        } else {
            stateInput.valueOptions = [];
            stateInput.isDisabled = true;
        }

        stateInput.value = '';
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

    formatSsn(): void {
        const { ssnLastFour } = this.formData;
        const format = (ssnInputVal) => {
            // Remove all non-dash and non-numerals
            const formatted = ssnInputVal.replace(/[^\d]/g, '');

            // Enforce max length
            return formatted.substring(0, 4);
        };

        ssnLastFour.value = format(ssnLastFour.value);
    }

    getCompactFromlicenseType(): string {
        const { licenseType: selectedLicenseType } = this.formValues;
        const licenseTypes = this.$tm('licensing.licenseTypes');
        let compactType = '';

        if (selectedLicenseType) {
            const foundlicenseType = licenseTypes.find((licenseType) => licenseType.key === selectedLicenseType);

            compactType = foundlicenseType.compactKey;
        }

        return compactType;
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const compact = this.getCompactFromlicenseType();
            const password = document.getElementById('password') as HTMLInputElement;

            if (!compact) {
                this.handleMissingCompactType();
            } else if (password?.value) {
                this.handleExtraFields();
            } else {
                const data = this.prepRequestData();

                await this.handleRecaptcha(data).catch(() => {
                    this.setError(this.$t('account.requestErrorRecaptcha'));
                });

                if (!this.isFormError) {
                    await this.$store.dispatch('user/createLicenseeAccountRequest', { compact, data }).catch((err) => {
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

    handleMissingCompactType(): void {
        this.setError(this.$t('account.requestErrorCompactMissing'));
        this.endFormLoading();
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
            ssnLastFour,
            dob,
            licenseState,
            licenseType,
        } = this.formValues;

        return {
            givenName: firstName,
            familyName: lastName,
            email,
            partialSocial: ssnLastFour,
            dob,
            jurisdiction: licenseState,
            licenseType,
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
        this.formData.licenseType.value = '';
        this.formData.licenseState.isDisabled = true;
        this.formData.licenseState.value = '';
        this.formData.firstName.value = '';
        this.formData.lastName.value = '';
        this.formData.email.value = '';
        this.formData.ssnLastFour.value = '';
        this.formData.dob.value = '';
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isConfirmationScreen = false;
        this.isFormError = false;
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    async mockPopulate(): Promise<void> {
        this.formData.licenseType.value = this.licenseTypeOptions[1]?.value || 'audiologist';
        await nextTick();
        this.populateStatesInput();
        await nextTick();
        this.formData.licenseState.value = this.stateOptions[1]?.value || 'co';
        this.formData.firstName.value = 'Test';
        this.formData.lastName.value = 'User';
        this.formData.email.value = 'test@example.com';
        this.formData.ssnLastFour.value = '1234';
        this.formData.dob.value = '2000-01-01';
        await nextTick();
        this.validateAll({ asTouched: true });
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

export default toNative(RegisterLicensee);

// export default RegisterLicensee;
