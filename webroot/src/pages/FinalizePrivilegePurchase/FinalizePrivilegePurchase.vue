<!--
    FinalizePrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 10/28/2024.
-->

<template>
    <div class="finalize-privilege-purchase-container">
        <form class="complete-purchase-form" @submit.prevent="handleSubmit">
            <div v-if="isMobile" class="button-row">
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
                            <InputText
                                :formInput="formData.firstName"
                            />
                            <InputText
                                :formInput="formData.lastName"
                            />
                        </div>
                         <div class="billing-address-section">
                            <div class="billing-address-title">
                                {{billingAddressTitleText}}
                            </div>
                            <InputText
                                :formInput="formData.firstName"
                            />
                            <InputText
                                :formInput="formData.lastName"
                            />
                            <div class="state-zip-line">
                            <InputText
                                :formInput="formData.firstName"
                            />
                            <InputText
                                :formInput="formData.lastName"
                            />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="cost-breakdown-container">
                    <div class="cost-listing-block">
                        Cost breakdown
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
