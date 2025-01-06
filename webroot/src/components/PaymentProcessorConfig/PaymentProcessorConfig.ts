//
//  PaymentProcessorConfig.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputPassword from '@components/Forms/InputPassword/InputPassword.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { CompactType, PaymentProcessorConfig as PaymentProcessorPayload } from '@models/Compact/Compact.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

@Component({
    name: 'PaymentProcessorConfig',
    components: {
        Card,
        MockPopulate,
        InputText,
        InputPassword,
        InputSubmit,
    }
})
class PaymentProcessorConfig extends mixins(MixinForm) {
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
        return (this.isFormLoading) ? this.$t('common.loading') : this.$t('common.submit');
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            accountId: new FormInput({
                id: 'payment-processor-account-id',
                name: 'payment-processor-account-id',
                label: computed(() => this.$t('compact.paymentProcessorAccountId')),
                validation: Joi.string().required().max(100).messages(this.joiMessages.string),
            }),
            accountKey: new FormInput({
                id: 'payment-processor-account-key',
                name: 'payment-processor-account-key',
                label: computed(() => this.$t('compact.paymentProcessorAccountKey')),
                validation: Joi.string().required().max(100).messages(this.joiMessages.string),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const compact = this.compactType || '';
            const { accountId, accountKey } = this.formValues;
            const payload: PaymentProcessorPayload = {
                apiLoginId: accountId,
                transactionKey: accountKey,
                processor: 'authorize.net',
            };

            await dataApi.updatePaymentProcessorConfig(compact, payload).catch((err) => {
                this.setError(err.message);
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                this.updateFormSubmitSuccess(this.$t('common.success'));
            }

            this.endFormLoading();
        }
    }

    async mockPopulate(): Promise<void> {
        this.populateFormInput(this.formData.accountId, 'test');
        this.populateFormInput(this.formData.accountKey, 'test');
    }
}

export default toNative(PaymentProcessorConfig);

// export default PaymentProcessorConfig;
