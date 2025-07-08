//
//  StateSettingsConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import {
    Component,
    mixins,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import {
    reactive,
    computed,
    ComputedRef,
    nextTick
} from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputEmailList from '@components/Forms/InputEmailList/InputEmailList.vue';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import Modal from '@components/Modal/Modal.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { CompactType, CompactStateConfig } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { formatCurrencyInput, formatCurrencyBlur } from '@models/_formatters/currency';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

interface RadioOption {
    value: boolean;
    name: string | ComputedRef<string>;
}

@Component({
    name: 'StateSettingsConfig',
    components: {
        Card,
        LoadingSpinner,
        MockPopulate,
        InputText,
        InputEmailList,
        InputRadioGroup,
        InputButton,
        InputSubmit,
        Modal,
    },
})
class StateSettingsConfig extends mixins(MixinForm) {
    @Prop({ required: true }) stateAbbrev!: string;

    //
    // Data
    //
    isLoading = false;
    loadingErrorMessage = '';
    initialStateConfig: CompactStateConfig | null = null;
    feeInputs: Array<FormInput> = [];
    isPurchaseEnabledInitialValue = false;
    isConfirmConfigModalDisplayed = false;

    //
    // Lifecycle
    //
    async created() {
        await this.init();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get compactType(): CompactType | null {
        return this.userStore?.currentCompact?.type || null;
    }

    get user(): StaffUser | null {
        return this.userStore?.model || null;
    }

    get submitLabel(): string {
        return (this.isFormLoading) ? this.$t('common.loading') : this.$t('common.saveChanges');
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    async init(): Promise<void> {
        this.shouldValuesIncludeDisabled = true;
        this.isLoading = true;

        if (this.compactType) {
            // Fetch compact config
            await this.getStateConfig();
            // Initialize the form
            this.initFormInputs();
        }
    }

    async getStateConfig(): Promise<void> {
        const compact = this.compactType || '';
        const licenseTypes = (this.$tm('licensing.licenseTypes') || []).filter((licenseType) =>
            licenseType.compactKey === compact);
        const stateConfig: any = await dataApi.getCompactStateConfig(compact, this.stateAbbrev).catch((err) => {
            this.loadingErrorMessage = err?.message || this.$t('serverErrors.networkError');
        });

        if (!this.loadingErrorMessage) {
            stateConfig?.privilegeFees?.forEach((privilegeFee) => {
                const licenseType = licenseTypes.find((type) => type.abbrev === privilegeFee.licenseTypeAbbreviation);

                privilegeFee.name = licenseType?.name || privilegeFee.licenseTypeAbbreviation?.toUpperCase() || '';
            });
            this.initialStateConfig = stateConfig;
            this.isPurchaseEnabledInitialValue = this.initialStateConfig?.licenseeRegistrationEnabled || false;
        }

        this.isLoading = false;
    }

    initFormInputs(): void {
        this.formData = reactive({
            isJurisprudenceExamRequired: new FormInput({
                id: 'jurisprudence-exam-required',
                name: 'jurisprudence-exam-required',
                label: computed(() => this.$t('compact.jurisprudenceExamRequired')),
                validation: Joi.boolean().required().messages(this.joiMessages.boolean),
                valueOptions: [
                    { value: true, name: computed(() => this.$t('common.yes')) },
                    { value: false, name: computed(() => this.$t('common.no')) },
                ] as Array<RadioOption>,
                value: this.initialStateConfig?.jurisprudenceRequirements?.required || false,
            }),
            jurisprudenceInfoLink: new FormInput({
                id: 'jurisprudence-info-link',
                name: 'jurisprudence-info-link',
                label: computed(() => this.$t('compact.jurisprudenceInfoLink')),
                labelSubtext: computed(() => this.$t('compact.jurisprudenceInfoLinkSubtext')),
                placeholder: 'https://',
                validation: Joi.string().uri().allow('').messages(this.joiMessages.string),
                value: this.initialStateConfig?.jurisprudenceRequirements?.linkToDocumentation || '',
            }),
            opsNotificationEmails: new FormInput({
                id: 'ops-notification-emails',
                name: 'ops-notification-emails',
                label: computed(() => this.$t('compact.opsNotificationEmails')),
                labelSubtext: computed(() => this.$t('compact.opsNotificationEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: this.initialStateConfig?.jurisdictionOperationsTeamEmails || [],
            }),
            adverseActionNotificationEmails: new FormInput({
                id: 'adverse-action-notification-emails',
                name: 'adverse-action-notification-emails',
                label: computed(() => this.$t('compact.adverseActionsNotificationEmails')),
                labelSubtext: computed(() => this.$t('compact.adverseActionsNotificationEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: this.initialStateConfig?.jurisdictionAdverseActionsNotificationEmails || [],
            }),
            summaryReportNotificationEmails: new FormInput({
                id: 'summary-report-notification-emails',
                name: 'summary-report-notification-emails',
                label: computed(() => this.$t('compact.summaryReportEmails')),
                labelSubtext: computed(() => this.$t('compact.summaryReportEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: this.initialStateConfig?.jurisdictionSummaryReportNotificationEmails || [],
            }),
            isPurchaseEnabled: new FormInput({
                id: 'purchase-enabled',
                name: 'purchase-enabled',
                label: computed(() => this.$t('compact.privilegePurchaseEnabled')),
                labelSubtext: computed(() => this.$t('compact.privilegePurchaseEnabledSubtext')),
                validation: Joi.boolean().required().messages(this.joiMessages.boolean),
                valueOptions: [
                    { value: true, name: computed(() => this.$t('common.yes')) },
                    { value: false, name: computed(() => this.$t('common.no')) },
                ] as Array<RadioOption>,
                value: this.initialStateConfig?.licenseeRegistrationEnabled || false,
                isDisabled: computed(() => this.isPurchaseEnabledInitialValue),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-compact-settings',
            }),
        });

        // Initialize the dynamic fee inputs
        this.initPrivilegeFeeInputs();

        this.watchFormInputs(); // Important if you want automated form validation
    }

    initPrivilegeFeeInputs(): void {
        this.initialStateConfig?.privilegeFees?.forEach((privilegeFee) => {
            const licenseType = privilegeFee.licenseTypeAbbreviation;
            const licenseTypeMilitary = `${licenseType}Military`;

            // Core license fee input
            this.formData[licenseType] = new FormInput({
                id: `${licenseType}-fee`,
                name: `${licenseType}-fee`,
                label: computed(() => {
                    const name = privilegeFee.name ?? '';
                    const capitalized = name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();

                    return (name)
                        ? `${capitalized} ${this.$t('compact.fee')}`
                        : this.$t('compact.fee');
                }),
                validation: Joi.number().required().min(0).messages(this.joiMessages.currency),
                value: privilegeFee.amount,
            });

            if (this.formData[licenseType].value) {
                this.formatBlur(this.formData[licenseType]);
            }

            // Military license fee input
            this.formData[licenseTypeMilitary] = new FormInput({
                id: `${licenseType}-fee-military`,
                name: `${licenseType}-fee-military`,
                label: computed(() => `${this.$t('compact.militaryAffiliated')} ${privilegeFee.name?.toLowerCase()} ${this.$t('compact.fee')}`),
                validation: Joi.number().min(0).allow(null, '').messages(this.joiMessages.currency),
                value: privilegeFee.militaryRate,
            });

            if (this.formData[licenseTypeMilitary].value) {
                this.formatBlur(this.formData[licenseTypeMilitary]);
            }

            this.feeInputs.push(this.formData[licenseType]);
            this.feeInputs.push(this.formData[licenseTypeMilitary]);
        });
    }

    formatInput(formInput: FormInput): void {
        const { value } = formInput;
        const formatted = formatCurrencyInput(value);

        // Update input value
        formInput.value = formatted;
    }

    formatBlur(formInput: FormInput, isOptional = false): void {
        const { value } = formInput;

        // Update input value
        if (value !== null && value !== '') {
            formInput.value = formatCurrencyBlur(value, isOptional);
        }
        // Validate as touched
        formInput.isTouched = true;
        formInput.validate();
    }

    async handleSubmit(isConfirmed = false): Promise<void> {
        this.populateOptionalMissing();
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            const { isPurchaseEnabled } = this.formValues;

            if (isPurchaseEnabled && !this.isPurchaseEnabledInitialValue && !isConfirmed) {
                this.openConfirmConfigModal();
            } else {
                this.startFormLoading();
                await this.processConfigUpdate();
                this.endFormLoading();
            }
        }
    }

    async processConfigUpdate(): Promise<void> {
        const compact = this.compactType || '';
        const {
            isJurisprudenceExamRequired,
            jurisprudenceInfoLink,
            opsNotificationEmails,
            adverseActionNotificationEmails,
            summaryReportNotificationEmails,
            isPurchaseEnabled,
        } = this.formValues;
        const feeInputsCore = this.feeInputs.filter((feeInput) => feeInput.id.endsWith('fee'));
        const payload: CompactStateConfig = {
            privilegeFees: feeInputsCore.map((feeInputCore) => {
                // Map indeterminate set of privilege fee inputs to their payload structure
                const [ licenseType ] = feeInputCore.id.split('-');
                const militaryInput = Object.values(this.formData).find((formInput) =>
                    (formInput as unknown as FormInput).id === `${feeInputCore.id}-military`) as FormInput | undefined;

                return {
                    licenseTypeAbbreviation: licenseType,
                    amount: Number(feeInputCore.value),
                    militaryRate: (militaryInput?.value === null || militaryInput?.value === '')
                        ? null
                        : Number(militaryInput?.value),
                };
            }),
            jurisprudenceRequirements: {
                required: isJurisprudenceExamRequired,
                linkToDocumentation: jurisprudenceInfoLink,
            },
            jurisdictionOperationsTeamEmails: opsNotificationEmails,
            jurisdictionAdverseActionsNotificationEmails: adverseActionNotificationEmails,
            jurisdictionSummaryReportNotificationEmails: summaryReportNotificationEmails,
            licenseeRegistrationEnabled: isPurchaseEnabled,
        };

        // Call the server API to update
        await dataApi.updateCompactStateConfig(compact, this.stateAbbrev, payload).catch((err) => {
            this.setError(err.message);
        });

        // Handle success
        if (!this.isFormError) {
            if (Object.prototype.hasOwnProperty.call(payload, 'licenseeRegistrationEnabled')) {
                this.isPurchaseEnabledInitialValue = (payload.licenseeRegistrationEnabled as boolean);
            }

            this.isFormSuccessful = true;
            this.updateFormSubmitSuccess(this.$t('compact.saveSuccessfulState'));
        }
    }

    populateMissingPurchaseEnabled(): void {
        if (this.formData.isPurchaseEnabled.value === '') {
            this.populateFormInput(this.formData.isPurchaseEnabled, false);
        }
    }

    populateOptionalMissing(): void {
        this.populateMissingPurchaseEnabled();
    }

    async openConfirmConfigModal(): Promise<void> {
        this.isConfirmConfigModalDisplayed = true;
        await nextTick();
        document.getElementById('confirm-modal-cancel-button')?.focus();
    }

    async closeConfirmConfigModal(): Promise<void> {
        this.isConfirmConfigModalDisplayed = false;
        await nextTick();
        document.getElementById(this.formData.submit.id)?.focus();
    }

    focusTrapConfirmConfigModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('confirm-modal-submit-button');
        const lastTabIndex = document.getElementById('confirm-modal-cancel-button');

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitConfirmConfigModal(): Promise<void> {
        this.closeConfirmConfigModal();
        await this.handleSubmit(true);
    }

    async mockPopulate(): Promise<void> {
        this.feeInputs.forEach((feeInput) => {
            this.populateFormInput(feeInput, 5);
        });
        this.populateFormInput(this.formData.isJurisprudenceExamRequired, true);
        this.populateFormInput(this.formData.jurisprudenceInfoLink, 'https://example.com');
        this.populateFormInput(this.formData.opsNotificationEmails, ['ops@example.com']);
        this.populateFormInput(this.formData.adverseActionNotificationEmails, ['adverse@example.com']);
        this.populateFormInput(this.formData.summaryReportNotificationEmails, ['summary@example.com']);
        this.populateFormInput(this.formData.isPurchaseEnabled, true);
    }

    //
    // Watch
    //
    @Watch('compactType') fetchStateConfig() {
        this.init();
    }
}

export default toNative(StateSettingsConfig);

// export default StateSettingsConfig;
