<!--
    PrivilegePurchaseAcceptUI.vue
    CompactConnect

    Created by InspiringApps on 5/29/2025.
-->

<template>
    <div class="accept-ui-container">
        <div class="accept-ui-button-container">
            <button
                type="button"
                class="AcceptUI btn-accept-ui"
                :class="{
                    'loading-init': isLoadingInit,
                    'include-icon': includeButtonIcon,
                    'warning': isWarning,
                }"
                :data-apiLoginID="loginId"
                :data-clientKey="clientKey"
                data-paymentOptions='{ "showCreditCard": true, "showBankAccount": false }'
                data-billingAddressOptions='{ "show": true, "required": true }'
                :data-acceptUIFormHeaderTxt="$t('payment.enterCardDetails')"
                :data-acceptUIFormBtnTxt="$t('payment.confirmCardDetails')"
                data-responseHandler="handlePaymentDetailsResponse"
                ref="acceptUi"
                :disabled="!isEnabled"
                @click="handleClicked"
            >
                <span v-if="isLoadingInit">{{ $t('common.loading') }}</span>
                <span v-else>{{ buttonLabelText }}</span>
            </button>
            <div v-if="includeButtonIcon" class="button-icon-container">
                <svg class="icon button-icon" fill="none" viewBox="0 0 24 24">
                <path d="M9 12L11 14L15 9.99999M20 12C20 16.4611 14.54 19.6937 12.6414 20.683C12.4361 20.79 12.3334
                    20.8435 12.191 20.8712C12.08 20.8928 11.92 20.8928 11.809 20.8712C11.6666 20.8435 11.5639 20.79
                    11.3586 20.683C9.45996 19.6937 4 16.4611 4 12V8.21759C4 7.41808 4 7.01833 4.13076 6.6747C4.24627
                    6.37113 4.43398 6.10027 4.67766 5.88552C4.9535 5.64243 5.3278 5.50207 6.0764 5.22134L11.4382
                    3.21067C11.6461 3.13271 11.75 3.09373 11.857 3.07827C11.9518 3.06457 12.0482 3.06457 12.143
                    3.07827C12.25 3.09373 12.3539 3.13271 12.5618 3.21067L17.9236 5.22134C18.6722 5.50207 19.0465
                    5.64243 19.3223 5.88552C19.566 6.10027 19.7537 6.37113 19.8692 6.6747C20 7.01833 20 7.41808
                    20 8.21759V12Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                />
                </svg>
            </div>
        </div>
        <div v-if="errorMessage" class="accept-ui-message-container error">
            <div>{{ errorMessage }}</div>
        </div>
        <div v-else-if="successMessage" class="accept-ui-message-container success">
            <div>{{ successMessage }}</div>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseAcceptUI.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseAcceptUI.less"></style>
