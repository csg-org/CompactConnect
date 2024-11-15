<!--
    SelectedStatePurchaseInformation.vue
    CompactConnect

    Created by InspiringApps on 11/12/2024.
-->

<template>
    <li class="selected-state-purchase-info-container">
        <div class="info-row">
            <div class="state-title">{{selectedStatePurchaseData.jurisdiction.name()}}</div>
            <InputButton
                label="X"
                :isTextLike="true"
                aria-label="deselect state"
                @click="deselectState()"
            />
        </div>
        <div class="info-row sub-row">
            <div class="info-row-label">{{expirationDateText}}</div>
            <div class="expire-date-value">{{activeLicenseExpirationDate}}</div>
        </div>
        <div class="info-row sub-row">
            <div class="info-row-label">{{jurisdictionFeeText}}</div>
            <div class="expire-date-value">${{feeDisplay}}</div>
        </div>
        <div class="info-row sub-row">
            <div class="info-row-label">{{commissionFeeText}}</div>
            <div class="expire-date-value">${{currentCompactCommissionFeeDisplay}}</div>
        </div>
        <div v-if="selectedStatePurchaseData.isMilitaryDiscountActive" class="info-row sub-row">
            <div class="info-row-label">{{militaryDiscountText}}</div>
            <div class="expire-date-value">-${{militaryDiscountAmountDisplay}}</div>
        </div>
        <div class="info-row">
            <div class="info-row-label">{{subtotalText}}</div>
            <div class="expire-date-value">${{subTotal}}</div>
        </div>
        <div v-if="state.isJurisprudenceRequired" class="jurisprudence-check-box">
            <InputCheckbox
                :formInput="jurisprudenceCheckInput"
                @change="handleJurisprudenceClicked()"
            />
        </div>
        <!-- <Modal
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
        </Modal> -->
    </li>
</template>

<script lang="ts" src="./SelectedStatePurchaseInformation.ts"></script>
<style scoped lang="less" src="./SelectedStatePurchaseInformation.less"></style>
