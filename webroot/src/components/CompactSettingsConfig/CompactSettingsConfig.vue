<!--
    CompactSettingsConfig.vue
    CompactConnect

    Created by InspiringApps on 5/13/2025.
-->

<template>
    <Card class="compact-config">
        <form class="compact-config-form" @submit.prevent="handleSubmit">
            <div class="compact-config-form-container">
                <h2 class="form-section-title fees">{{ $t('compact.privilegeFees') }}</h2>
                <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                <InputText
                    :formInput="formData.compactFee"
                    class="form-row currency"
                    @input="formatCurrencyInput(formData.compactFee)"
                    @blur="formatCurrencyBlur(formData.compactFee)"
                />
                <InputText
                    :formInput="formData.privilegeTransactionFee"
                    class="form-row currency"
                     @input="formatCurrencyInput(formData.privilegeTransactionFee)"
                    @blur="formatCurrencyBlur(formData.privilegeTransactionFee, true)"
                />
                <h2 class="form-section-title notifications">{{ $t('compact.notifications') }}</h2>
                <InputEmailList :formInput="formData.opsNotificationEmails" />
                <InputEmailList :formInput="formData.adverseActionNotificationEmails" />
                <InputEmailList :formInput="formData.summaryReportNotificationEmails" />
                <h2 class="form-section-title live-status">{{ $t('compact.licenseRegistrationTitle') }}</h2>
                <InputRadioGroup
                    :formInput="formData.isRegistrationEnabled"
                    class="form-row"
                    @blur="populateMissingRegistrationEnabled"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                    class="compact-config-submit"
                />
            </div>
        </form>
    </Card>
</template>

<script lang="ts" src="./CompactSettingsConfig.ts"></script>
<style scoped lang="less" src="./CompactSettingsConfig.less"></style>
