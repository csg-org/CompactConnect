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
import { CompactType, CompactStateConfig /* , FeeType */ } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { formatCurrencyInput, formatCurrencyBlur } from '@models/_formatters/currency';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

interface PurchaseEnabledOption {
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
    initialStateConfig: any = {};
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
        return this.userStore.currentCompact?.type;
    }

    get user(): StaffUser | null {
        return this.userStore.model;
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

            // @TODO
            // Format existing values
            // const { compactFee, privilegeTransactionFee } = this.formData;
            //
            // if (compactFee?.value) {
            //     this.formatBlur(this.formData.compactFee);
            // }
            //
            // if (privilegeTransactionFee?.value) {
            //     this.formatBlur(this.formData.privilegeTransactionFee, true);
            // }
        }
    }

    async getStateConfig(): Promise<void> {
        const compact = this.compactType || '';
        const stateConfig = await dataApi.getCompactStateConfig(compact, this.stateAbbrev).catch((err) => {
            this.loadingErrorMessage = err?.message || this.$t('serverErrors.networkError');
        });

        this.initialStateConfig = stateConfig;
        this.isPurchaseEnabledInitialValue = this.initialStateConfig?.licenseeRegistrationEnabled;
        this.isLoading = false;
    }

    initFormInputs(): void {
        this.formData = reactive({
            // @TODO
            // compactFee: new FormInput({
            //     id: 'compact-fee',
            //     name: 'compact-fee',
            //     label: computed(() => this.$t('compact.compactFee')),
            //     validation: Joi.number().required().min(0).messages(this.joiMessages.currency),
            //     value: this.initialStateConfig?.compactCommissionFee?.feeAmount,
            // }),
            // privilegeTransactionFee: new FormInput({
            //     id: 'privilege-transaction-fee',
            //     name: 'privilege-transaction-fee',
            //     label: computed(() => this.$t('compact.privilegeTransactionFee')),
            //     validation: Joi.number().min(0).messages(this.joiMessages.currency),
            //     value: this.initialStateConfig?.transactionFeeConfiguration?.licenseeCharges?.chargeAmount,
            // }),
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
                ] as Array<PurchaseEnabledOption>,
                value: this.initialStateConfig?.licenseeRegistrationEnabled || false,
                isDisabled: computed(() => this.isPurchaseEnabledInitialValue),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-compact-settings',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    formatInput(formInput: FormInput): void {
        const { value } = formInput;
        const formatted = formatCurrencyInput(value);

        // Update input value
        formInput.value = formatted;
    }

    formatBlur(formInput: FormInput, isOptional = false): void {
        const { value } = formInput;
        const formatted = formatCurrencyBlur(value, isOptional);

        // Update input value
        formInput.value = formatted;
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
            // @TODO
            // compactFee,
            // privilegeTransactionFee,
            opsNotificationEmails,
            adverseActionNotificationEmails,
            summaryReportNotificationEmails,
            isPurchaseEnabled,
        } = this.formValues;
        const payload: CompactStateConfig = {
            privilegeFees: [],
            jurisprudenceRequirements: {
                required: false,
                linkToDocumentation: '',
            },
            // compactCommissionFee: {
            //     feeType: FeeType.FLAT_RATE,
            //     feeAmount: Number(compactFee),
            // },
            jurisdictionOperationsTeamEmails: opsNotificationEmails,
            jurisdictionAdverseActionsNotificationEmails: adverseActionNotificationEmails,
            jurisdictionSummaryReportNotificationEmails: summaryReportNotificationEmails,
            // transactionFeeConfiguration: {
            //     licenseeCharges: {
            //         active: true,
            //         chargeType: FeeType.FLAT_FEE_PER_PRIVILEGE,
            //         chargeAmount: Number(privilegeTransactionFee),
            //     },
            // },
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

    // @TODO
    // populateMissingPrivilegeTransactionFee(): void {
    //     if (this.formData.privilegeTransactionFee.value === '') {
    //         this.populateFormInput(this.formData.privilegeTransactionFee, 0);
    //     }
    // }

    populateMissingPurchaseEnabled(): void {
        if (this.formData.isPurchaseEnabled.value === '') {
            this.populateFormInput(this.formData.isPurchaseEnabled, false);
        }
    }

    populateOptionalMissing(): void {
        // this.populateMissingPrivilegeTransactionFee();
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
        // @TODO
        // this.populateFormInput(this.formData.compactFee, 5.55);
        // this.populateFormInput(this.formData.privilegeTransactionFee, 5);
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
