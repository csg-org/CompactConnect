<!--
    SelectPrivileges.vue
    CompactConnect

    Created by InspiringApps on 10/15/2024.
-->

<template>
    <div class="select-privileges-container">
        <form class="privilege-form" @submit.prevent="handleSubmit">
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
            <div class="select-privileges-core-container">
                <div class="select-privileges-title">
                    {{selectPrivilegesTitleText}}
                </div>
                <div class="state-select-list">
                    <div
                        v-for="state in stateCheckList"
                        :key="state.label"
                        class="state-select-unit"
                    >
                        <div v-if="state.isDisabled" class="disabled-state-overlay" />
                        <InputCheckbox
                            :formInput="state"
                            :isDisabled="state.isDisabled"
                            @change="handleStateClicked"
                        />
                    </div>
                </div>
                <div class="selected-state-list">
                    <div
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
                            <div class="expire-date-value">${{state.fee}}</div>
                        </div>
                        <div class="info-row sub-row">
                            <div class="info-row-label">{{commissionFeeText}}</div>
                            <div class="expire-date-value">${{currentCompactCommissionFee}}</div>
                        </div>
                        <div v-if="state.isMilitaryDiscountActive" class="info-row sub-row">
                            <div class="info-row-label">{{militaryDiscountText}}</div>
                            <div class="expire-date-value">-${{state.militaryDiscountAmount}}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-row-label">{{subtotalText}}</div>
                            <div class="expire-date-value">${{subTotalList[i]}}</div>
                        </div>
                        <div v-if="state.isJurisprudenceRequired" class="jurisprudence-check-box">
                            <InputCheckbox
                                :formInput="formData.jurisprudenceConfirmations[state.jurisdiction.abbrev]"
                                @change="handleJurisprudenceClicked"
                            />
                        </div>
                    </div>
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
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./SelectPrivileges.ts"></script>
<style scoped lang="less" src="./SelectPrivileges.less"></style>
