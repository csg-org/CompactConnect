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
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen"
                    />
                </div>
            </div>
            <div class="finalize-purchase-core-container">
                <div class="finalize-purchase-title">
                    {{selectPrivilegesTitleText}}
                </div>
                <div class="lists-container">
                    <ul class="state-select-list">
                        <li
                            v-for="state in stateCheckList"
                            :key="state.label"
                        >
                            <div v-if="checkIfStateSelectIsDisabled(state)" class="state-select-unit">
                                <div class="disabled-state-overlay" />
                                <InputCheckbox
                                    :formInput="state"
                                />
                            </div>
                            <div
                                v-else
                                class="state-select-unit"
                                @click.stop="checkState(state)"
                                @keyup.enter="checkState(state)"
                                tabindex="0"
                            >
                                <InputCheckbox
                                    :formInput="state"
                                    @change="handleStateClicked(state)"
                                />
                            </div>
                        </li>
                    </ul>
                    <ul class="selected-state-list">
                        <li
                            v-for="(state, i) in selectedStatePurchaseDataList"
                            :key="state.jurisdiction.abbrev"
                            class="selected-state-block"
                        >
                            <div class="info-row">
                                <div class="state-title">{{state.jurisdiction.name()}}</div>
                                <InputButton
                                    label="X"
                                    :isTextLike="true"
                                    aria-label="deselect state"
                                    @click="deselectState(state)"
                                />
                            </div>
                            <div class="info-row sub-row">
                                <div class="info-row-label">{{expirationDateText}}</div>
                                <div class="expire-date-value">{{activeLicenseExpirationDate}}</div>
                            </div>
                            <div class="info-row sub-row">
                                <div class="info-row-label">{{jurisdictionFeeText}}</div>
                                <div class="expire-date-value">${{state.fee.toFixed(2)}}</div>
                            </div>
                            <div class="info-row sub-row">
                                <div class="info-row-label">{{commissionFeeText}}</div>
                                <div class="expire-date-value">${{currentCompactCommissionFee.toFixed(2)}}</div>
                            </div>
                            <div v-if="state.isMilitaryDiscountActive" class="info-row sub-row">
                                <div class="info-row-label">{{militaryDiscountText}}</div>
                                <div class="expire-date-value">-${{state.militaryDiscountAmount.toFixed(2)}}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-row-label">{{subtotalText}}</div>
                                <div class="expire-date-value">${{subTotalList[i].toFixed(2)}}</div>
                            </div>
                            <div v-if="state.isJurisprudenceRequired" class="jurisprudence-check-box">
                                <InputCheckbox
                                    :formInput="formData.jurisprudenceConfirmations[state.jurisdiction.abbrev]"
                                    @change="handleJurisprudenceClicked(state)"
                                />
                            </div>
                        </li>
                    </ul>
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
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen && areAllJurisprudenceConfirmed"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./FinalizePrivilegePurchase.ts"></script>
<style scoped lang="less" src="./FinalizePrivilegePurchase.less"></style>
