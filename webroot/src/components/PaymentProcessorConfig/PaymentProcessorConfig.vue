<!--
    PaymentProcessorConfig.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Card class="payment-processor">
        <div class="payment-processor-form">
            <h2>{{ $t('compact.paymentProcessorCredentials') }}</h2>
            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
            <div class="payment-processor-form-container">
                <form @submit.prevent="handleSubmit">
                    <InputText class="rr-block" :formInput="formData.accountId" />
                    <InputPassword
                        :formInput="formData.accountKey"
                        :joiMessages="joiMessages"
                        :showEyeIcon="true"
                        :showRequirements="false"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading"
                        class="payment-processer-submit"
                    />
                </form>
            </div>
        </div>
    </Card>
</template>

<script lang="ts" src="./PaymentProcessorConfig.ts"></script>
<style scoped lang="less" src="./PaymentProcessorConfig.less"></style>
