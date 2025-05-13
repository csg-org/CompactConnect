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
                validation: Joi.number().required().min(0).messages(this.joiMessages.number),
            }),
            privilegeTransactionFee: new FormInput({
                id: 'privilege-transaction-fee',
                name: 'privilege-transaction-fee',
                label: computed(() => this.$t('compact.privilegeTransactionFee')),
                validation: Joi.number().min(0).messages(this.joiMessages.number),
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

    async handleSubmit(): Promise<void> {
        this.populateOptionalMissing();
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            // const compact = this.compactType || '';
            // const { accountId, accountKey } = this.formValues;
            // const payload: PaymentProcessorPayload = {
            //     apiLoginId: accountId,
            //     transactionKey: accountKey,
            //     processor: 'authorize.net',
            // };
            //
            // await dataApi.updatePaymentProcessorConfig(compact, payload).catch((err) => {
            //     this.setError(err.message);
            // });
            //
            // if (!this.isFormError) {
            //     this.isFormSuccessful = true;
            //     this.updateFormSubmitSuccess(this.$t('common.success'));
            // }

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
        this.populateFormInput(this.formData.compactFee, 50);
        this.populateFormInput(this.formData.privilegeTransactionFee, 5);
        this.populateFormInput(this.formData.isRegistrationEnabled, false);
    }
}

export default toNative(CompactSettingsConfig);

// export default CompactSettingsConfig;
