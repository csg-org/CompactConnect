<!--
    PrivilegePurchaseFinalize.vue
    CompactConnect

    Created by InspiringApps on 10/28/2024.
-->

<template>
    <div class="finalize-privilege-purchase-container">
        <form class="complete-purchase-form" @submit.prevent="handleSubmit">
            <div class="finalize-purchase-container">
                <div class="finalize-purchase-core-container">
                    <div class="finalize-purchase-title-row">
                        <h1 class="finalize-purchase-title">{{paymentTitleText}}</h1>
                        <CollapseCaretButton v-if="isPhone" @toggleCollapse="togglePaymentCollapsed" />
                    </div>
                    <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                    <div v-if="shouldShowPaymentSection || !isPhone" class="payment-core-form">
                        <div class="credit-card-section">
                            <div class="credit-card-title">{{creditCardTitleText}}</div>
                            <div class="form-row">
                                <InputCreditCard :formInput="formData.creditCard" @input="formatCreditCard()" />
                            </div>
                            <div class="cc-dets form-row">
                                <div class="exp-chunk">
                                    <div class="exp-chunk-title">{{expirationDateText}} *</div>
                                    <div class="exp-chunk-input">
                                        <InputText
                                            :formInput="formData.expMonth"
                                            @input="handleExpMonthInput(formData.expMonth)"
                                        />
                                        <div class="slash">/</div>
                                        <InputText
                                            :formInput="formData.expYear"
                                            @input="handleExpYearInput(formData.expYear)"
                                            @emitInputRef="handleExpYearRefEmitted"
                                        />
                                    </div>
                                </div>
                                <div class="cvv-container">
                                    <InputText
                                        :formInput="formData.cvv"
                                        @input="handleCVVInput(formData.cvv)"
                                        @emitInputRef="handleCVVRefEmitted"
                                    />
                                </div>
                            </div>
                        </div>
                        <div class="billing-address-section">
                            <div class="billing-address-title">{{billingAddressTitleText}}</div>
                            <div class="form-row">
                                <InputText :formInput="formData.firstName" />
                            </div>
                            <div class="form-row">
                                <InputText :formInput="formData.lastName" />
                            </div>
                            <div class="form-row">
                                <InputText :formInput="formData.streetAddress1" />
                            </div>
                            <div class="form-row">
                                <InputText :formInput="formData.streetAddress2" />
                            </div>
                            <div class="state-zip-line form-row">
                                <InputSelect :formInput="formData.stateSelect" class="state-select" />
                                <InputText
                                    :formInput="formData.zip"
                                    @input="handleZipInput(formData.cvv)"
                                />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="cost-breakdown-container">
                    <div class="cost-listing-block">
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
                                    <div class="info-row-amount">-${{state.stateMilitaryDiscountAmountDisplay}}</div>
                                </div>
                            </li>
                        </ul>
                        <div class="compact-commission-fee info-row">
                            <div class="info-row-label">{{compactCommissionFeeText}}</div>
                            <div class="info-row-amount">${{totalCompactCommissionFeeDisplay}}</div>
                        </div>
                        <div class="section-title">{{feesText}}</div>
                            <div class="info-row">
                                <div class="info-row-label">{{creditCardFeesText}}</div>
                                <div class="info-row-amount">${{creditCardFeesTotal}}</div>
                            </div>
                        <div class="purchase-total info-row">
                            <div class="info-row-label total">{{totalTitle}}</div>
                            <div class="info-row-amount total">${{totalPurchasePriceDisplay}}</div>
                        </div>
                    </div>
                    <InputCheckbox :formInput="formData.noRefunds" class="no-refunds-checkbox" />
                </div>
            </div>
            <div v-if="formErrorMessage" class="form-error-message">{{formErrorMessage}}</div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="cancel-button"
                    @click="handleCancelClicked"
                />
                <div class="right-cell">
                    <InputButton
                        :label="backText"
                        :isTransparent="true"
                        aria-label="close modal"
                        class="back-button"
                        @click="handleBackClicked"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading && isSubmitEnabled"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseFinalize.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseFinalize.less"></style>
