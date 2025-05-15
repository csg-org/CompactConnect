//
//  CompactSettingsConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputEmailList from '@components/Forms/InputEmailList/InputEmailList.vue';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { CompactType } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
// import { dataApi } from '@network/data.api';
import Joi from 'joi';

interface RegistrationEnabledOption {
    value: boolean;
    name: string | ComputedRef<string>;
}

@Component({
    name: 'CompactSettingsConfig',
    components: {
        Card,
        MockPopulate,
        InputText,
        InputEmailList,
        InputRadioGroup,
        InputSubmit,
    }
})
class CompactSettingsConfig extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
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
    initFormInputs(): void {
        this.formData = reactive({
            compactFee: new FormInput({
                id: 'compact-fee',
                name: 'compact-fee',
                label: computed(() => this.$t('compact.compactFee')),
                validation: Joi.number().required().min(0).messages(this.joiMessages.currency),
            }),
            privilegeTransactionFee: new FormInput({
                id: 'privilege-transaction-fee',
                name: 'privilege-transaction-fee',
                label: computed(() => this.$t('compact.privilegeTransactionFee')),
                validation: Joi.number().min(0).messages(this.joiMessages.currency),
            }),
            opsNotificationEmails: new FormInput({
                id: 'ops-notification-emails',
                name: 'ops-notification-emails',
                label: computed(() => this.$t('compact.opsNotificationEmails')),
                labelSubtext: computed(() => this.$t('compact.opsNotificationEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: [] as Array<string>,
            }),
            adverseActionNotificationEmails: new FormInput({
                id: 'adverse-action-notification-emails',
                name: 'adverse-action-notification-emails',
                label: computed(() => this.$t('compact.adverseActionsNotificationEmails')),
                labelSubtext: computed(() => this.$t('compact.adverseActionsNotificationEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: [] as Array<string>,
            }),
            summaryReportNotificationEmails: new FormInput({
                id: 'summary-report-notification-emails',
                name: 'summary-report-notification-emails',
                label: computed(() => this.$t('compact.summaryReportEmails')),
                labelSubtext: computed(() => this.$t('compact.summaryReportEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(1).messages(this.joiMessages.array),
                value: [] as Array<string>,
            }),
            isRegistrationEnabled: new FormInput({
                id: 'registration-enabled',
                name: 'registration-enabled',
                label: computed(() => this.$t('compact.licenseRegistrationEnabled')),
                labelSubtext: computed(() => this.$t('compact.licenseRegistrationEnabledSubtext')),
                validation: Joi.boolean().required().messages(this.joiMessages.boolean),
                valueOptions: [
                    { value: true, name: computed(() => this.$t('common.yes')) },
                    { value: false, name: computed(() => this.$t('common.no')) },
                ] as Array<RegistrationEnabledOption>,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-compact-settings',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    formatCurrencyInput(formInput: FormInput): void {
        const { value } = formInput;
        let [ dollars, cents ] = value.toString().split(/\.(.*)/s);
        const hasDecimal = cents !== undefined;
        let formatted = '';

        // Get raw dollar & cent values
        dollars = dollars.replace(/\D/g, '');
        cents = (hasDecimal) ? cents.replace(/\D/g, '') : '';

        // Prevent cents from having too many decimal places
        if (cents.length > 2) {
            cents = cents.slice(0, 2);
        }

        // Format with typing-in-progress allowances
        if (dollars && hasDecimal) {
            formatted = `${dollars}.${cents}`;
        } else if (dollars) {
            formatted = `${dollars}`;
        } else if (cents) {
            formatted = `0.${cents}`;
        }

        // Update input value
        formInput.value = formatted;
    }

    formatCurrencyBlur(formInput: FormInput, isOptional = false): void {
        const { value } = formInput;
        let [ dollars, cents ] = value.toString().split(/\.(.*)/s);
        let formatted = '';

        if (!value && isOptional) {
            // Autofill if optional input is blank
            dollars = '0';
        } else if (cents?.length === 1) {
            // Add trailing digit to cents if needed
            cents += '0';
        }

        // Format with done-typing cleanups
        if (dollars && cents) {
            formatted = `${dollars}.${cents}`;
        } else if (dollars) {
            formatted = `${dollars}`;
        } else if (cents) {
            formatted = `0.${cents}`;
        }

        // Update input value
        formInput.value = formatted;
        // Validate as touched
        formInput.isTouched = true;
        formInput.validate();
    }

    async handleSubmit(): Promise<void> {
        this.populateOptionalMissing();
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            // const compact = this.compactType || '';
            const {
                compactFee,
                privilegeTransactionFee,
                opsNotificationEmails,
                adverseActionNotificationEmails,
                summaryReportNotificationEmails,
                isRegistrationEnabled,
            } = this.formValues;
            const payload = {
                compactCommissionFee: {
                    feeType: 'FLAT_RATE',
                    feeAmount: Number(compactFee),
                },
                licenseeRegistrationEnabled: isRegistrationEnabled,
                compactOperationsTeamEmails: opsNotificationEmails,
                compactAdverseActionsNotificationEmails: adverseActionNotificationEmails,
                compactSummaryReportNotificationEmails: summaryReportNotificationEmails,
                transactionFeeConfiguration: {
                    licenseeCharges: {
                        active: true,
                        chargeType: 'FLAT_FEE_PER_PRIVILEGE',
                        chargeAmount: Number(privilegeTransactionFee),
                    },
                },
            };

            // @TODO
            console.log('submit!');
            console.log(JSON.stringify(payload, null, 2));
            console.log('');
            await new Promise((resolve) => setTimeout(() => { resolve(true); }, 500));
            // await dataApi.updateCompactConfig(compact, payload).catch((err) => {
            //     this.setError(err.message);
            // });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.updateFormSubmitSuccess(this.$t('compact.saveSuccessfulCompact'));
            }

            this.endFormLoading();
        }
    }

    populateMissingPrivilegeTransactionFee(): void {
        if (this.formData.privilegeTransactionFee.value === '') {
            this.populateFormInput(this.formData.privilegeTransactionFee, 0);
        }
    }

    populateMissingRegistrationEnabled(): void {
        if (this.formData.isRegistrationEnabled.value === '') {
            this.populateFormInput(this.formData.isRegistrationEnabled, false);
        }
    }

    populateOptionalMissing(): void {
        this.populateMissingPrivilegeTransactionFee();
        this.populateMissingRegistrationEnabled();
    }

    async mockPopulate(): Promise<void> {
        this.populateFormInput(this.formData.compactFee, 5.55);
        this.populateFormInput(this.formData.privilegeTransactionFee, 5);
        this.populateFormInput(this.formData.opsNotificationEmails, ['test@inspiringapps.com']);
        this.populateFormInput(this.formData.adverseActionNotificationEmails, ['test@inspiringapps.com']);
        this.populateFormInput(this.formData.summaryReportNotificationEmails, ['test@inspiringapps.com']);
        this.populateFormInput(this.formData.isRegistrationEnabled, false);
    }
}

export default toNative(CompactSettingsConfig);

// export default CompactSettingsConfig;
