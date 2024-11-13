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
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen && areAllJurisprudenceConfirmed"
                    />
                </div>
            </div>
            <div class="select-privileges-core-container">
                <div class="select-privileges-title">
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
                            >
                                <div
                                    @click.prevent="toggleStateSelected(state)"
                                    @keyup.enter="toggleStateSelected(state)"
                                    tabindex="0"
                                    class="enabled-state-overlay"
                                />
                                <InputCheckbox
                                    :formInput="state"
                                />
                            </div>
                        </li>
                    </ul>
                    <ul v-if="isPhone" class="selected-state-list">
                        <SelectedStatePurchaseInformation
                            v-for="(state, i) in selectedStatePurchaseDataDisplayList"
                            :key="state.jurisdiction.abbrev"
                            class="selected-state-block"
                            
                        />
                        <!-- <li
                            v-for="(state, i) in selectedStatePurchaseDataDisplayList"
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
                                <div class="expire-date-value">${{state.feeDisplay}}</div>
                            </div>
                            <div class="info-row sub-row">
                                <div class="info-row-label">{{commissionFeeText}}</div>
                                <div class="expire-date-value">${{currentCompactCommissionFeeDisplay}}</div>
                            </div>
                            <div v-if="state.isMilitaryDiscountActive" class="info-row sub-row">
                                <div class="info-row-label">{{militaryDiscountText}}</div>
                                <div class="expire-date-value">-${{state.militaryDiscountAmountDisplay}}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-row-label">{{subtotalText}}</div>
                                <div class="expire-date-value">${{subTotalListDisplay[i]}}</div>
                            </div>
                            <div v-if="state.isJurisprudenceRequired" class="jurisprudence-check-box">
                                <InputCheckbox
                                    :formInput="formData.jurisprudenceConfirmations[state.jurisdiction.abbrev]"
                                    @change="handleJurisprudenceClicked(state)"
                                />
                            </div>
                        </li> -->
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
        <Modal
            v-if="shouldShowJurisprudenceModal"
            class="jurisprudence-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="jurisprudenceModalTitle"
            @close-modal="closeAndInvalidateCheckbox"
        >
            <template v-slot:content>
                <div class="jurisprudence-modal-content">
                    {{jurisprudenceModalContent}}
                    <div class="action-button-row">
                        <InputButton
                            class="back-button"
                            :label="backText"
                            :isTransparent="true"
                            :onClick="closeAndInvalidateCheckbox"
                        />
                        <InputButton
                            class="understand-button"
                            :label="iUnderstandText"
                            :onClick="submitUnderstanding"
                        />
                    </div>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script lang="ts" src="./SelectPrivileges.ts"></script>
<style scoped lang="less" src="./SelectPrivileges.less"></style>
