<!--
    FinalizePrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 10/28/2024.
-->

<template>
    <div class="finalize-privilege-purchase-container">
        <form class="complete-purchase-form" @submit.prevent="handleSubmit">
            <div class="finalize-purchase-container">
                <div class="finalize-purchase-core-container">
                    <div class="finalize-purchase-title">
                        {{paymentTitleText}}
                    </div>
                    <div class="payment-core-form">
                        <div class="credit-card-section">
                            <div class="credit-card-title">
                                {{creditCardTitleText}}
                            </div>
                            <div class="form-row">
                                <InputText
                                    :formInput="formData.firstName"
                                />
                            </div>
                            <div class="form-row">
                                <InputText
                                    :formInput="formData.lastName"
                                />
                            </div>
                            <div class="form-row">
                                <InputCreditCard
                                    :formInput="formData.creditCard"
                                />
                            </div>
                            <div class="cc-dets form-row">
                                <div class="exp-chunk">
                                    <div class="exp-chunk-title">
                                        {{expirationDateText}} *
                                    </div>
                                    <div class="exp-chunk-input">
                                        <InputNumber
                                            :formInput="formData.expMonth"
                                        />
                                        <div class="slash">
                                            /
                                        </div>
                                        <InputNumber
                                            :formInput="formData.expYear"
                                        />
                                    </div>
                                </div>
                                <div class="cvv-container">
                                    <InputNumber
                                        :formInput="formData.cvv"
                                    />
                                </div>
                            </div>
                        </div>
                        <div class="billing-address-section">
                            <div class="billing-address-title">
                                {{billingAddressTitleText}}
                            </div>
                            <div class="form-row">
                                <InputText
                                    :formInput="formData.streetAddress1"
                                />
                            </div>
                            <div class="form-row">
                                <InputText
                                    :formInput="formData.streetAddress2"
                                />
                            </div>
                            <div class="state-zip-line form-row">
                                <InputSelect
                                    :formInput="formData.stateSelect"
                                />
                                <InputNumber
                                    :formInput="formData.zip"
                                />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="cost-breakdown-container">
                    <div class="cost-listing-block">
                        <div class="selection-title">{{selectionText}}</div>
                        <ul>
                            <li
                                v-for="(state) in selectedStatePurchaseDataList"
                                :key="state.jurisdiction.abbrev"
                                class="selected-state-block"
                            >
                                <div class="info-row">
                                    <div class="info-row-label">
                                        {{`${state?.jurisdiction?.name()} ${compactPrivilegeStateFeeText}`}}
                                    </div>
                                    <div class="expire-date-value">${{state?.fee?.toFixed(2)}}</div>
                                </div>
                                <div v-if="state.isMilitaryDiscountActive" class="info-row">
                                    <div class="info-row-label">
                                        {{`${state?.jurisdiction?.name()} ${militaryDiscountText}`}}
                                    </div>
                                    <div class="expire-date-value">-${{state?.militaryDiscountAmount?.toFixed(2)}}</div>
                                </div>
                            </li>
                        </ul>
                        <div class="compact-commission-fee info-row">
                            <div class="info-row-label">
                                {{compactCommissionFeeText}}
                            </div>
                            <div class="expire-date-value">${{totalCompactCommissionFee?.toFixed(2)}}</div>
                        </div>
                        <div class="purchase-total info-row">
                            <div class="info-row-label total">
                                {{totalTitle}}
                            </div>
                            <div class="expire-date-value total">${{totalPurchasePrice?.toFixed(2)}}</div>
                        </div>
                    </div>
                    <InputCheckbox :formInput="formData.noRefunds" />
                </div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="icon icon-close-modal"
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
                        :isEnabled="!isFormLoading"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./FinalizePrivilegePurchase.ts"></script>
<style scoped lang="less" src="./FinalizePrivilegePurchase.less"></style>
