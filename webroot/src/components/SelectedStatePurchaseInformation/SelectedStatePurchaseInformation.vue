<!--
    SelectedStatePurchaseInformation.vue
    CompactConnect

    Created by InspiringApps on 11/12/2024.
-->

<template>
    <li class="selected-state-purchase-info-container">
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
    </li>

</template>

<script lang="ts" src="./SelectedStatePurchaseInformation.ts"></script>
<style scoped lang="less" src="./SelectedStatePurchaseInformation.less"></style>
