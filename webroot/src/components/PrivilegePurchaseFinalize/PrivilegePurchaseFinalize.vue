<!--
    PrivilegePurchaseFinalize.vue
    CompactConnect

    Created by InspiringApps on 10/28/2024.
-->

<template>
    <div id="finalize-privilege-purchase-container" class="finalize-privilege-purchase-container">
        <form class="complete-purchase-form" @submit.prevent="() => null">
            <div class="finalize-purchase-container">
                <div class="finalize-purchase-title-row">
                    <h1 class="finalize-purchase-title">{{$t('payment.paymentSummary')}}</h1>
                </div>
                <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                <div class="cost-breakdown-container">
                    <div class="cost-listing-block">
                        <div class="cost-section">
                            <div class="section-title">{{selectionText}}</div>
                            <ul>
                                <li
                                    v-for="(state) in selectedStatePurchaseDisplayDataList"
                                    :key="state.jurisdiction.abbrev"
                                    class="selected-state-block"
                                >
                                    <div class="info-row">
                                        <div class="info-row-label">{{state.stateFeeText}}</div>
                                        <div class="info-row-amount">${{state.stateFeeDisplay}}</div>
                                    </div>
                                    <div v-if="state.isMilitaryDiscountActive" class="info-row">
                                        <div class="info-row-label">{{state.stateMilitaryPurchaseText}}</div>
                                        <div class="info-row-amount">
                                            -${{state.stateMilitaryDiscountAmountDisplay}}
                                        </div>
                                    </div>
                                </li>
                            </ul>
                            <div class="compact-commission-fee info-row">
                                <div class="info-row-label">{{compactCommissionFeeText}}</div>
                                <div class="info-row-amount">${{totalCompactCommissionFeeDisplay}}</div>
                            </div>
                            <div v-if="isPerPrivilegeTransactionFeeActive" class="info-row">
                                <div class="info-row-label">{{$t('payment.ccTransactionFees')}}</div>
                                <div class="info-row-amount">${{creditCardFeesTotalDisplay}}</div>
                            </div>
                        </div>
                        <div class="purchase-total info-row">
                            <div class="info-row-label total">{{$t('common.total')}}</div>
                            <div class="info-row-amount total">${{totalPurchasePriceDisplay}}</div>
                        </div>
                    </div>
                    <InputCheckbox :formInput="formData.noRefunds" class="no-refunds-checkbox" />
                </div>
            </div>
            <div v-if="formErrorMessage" class="form-error-message">{{formErrorMessage}}</div>
            <div id="button-row" class="button-row">
                <div class="form-nav-buttons">
                    <div class="payment-button-container">
                        <InputButton
                            v-if="!isSubmitEnabled"
                            :label="$t('payment.payment')"
                            :isDisabled="isFormLoading || !isSubmitEnabled"
                            class="payment-overlay-button"
                            @click="handlePaymentButtonClick"
                        />
                        <PrivilegePurchaseAcceptUI
                            class="form-nav-button accept-ui"
                            :paymentSdkConfig="currentCompactPaymentSdkConfig"
                            :buttonLabel="$t('payment.payment')"
                            :isEnabled="!isFormLoading && isSubmitEnabled"
                            @success="acceptUiSuccessResponse"
                            @error="acceptUiErrorResponse"
                        />
                    </div>
                    <InputButton
                        :label="$t('common.back')"
                        :isTransparent="true"
                        aria-label="close modal"
                        class="form-nav-button back-button"
                        @click="handleBackClicked"
                    />
                </div>
                <div class="form-override-buttons">
                    <InputButton
                        :label="$t('common.cancel')"
                        :isTextLike="true"
                        aria-label="close modal"
                        class="form-override-button cancel-button"
                        @click="handleCancelClicked"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseFinalize.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseFinalize.less"></style>
