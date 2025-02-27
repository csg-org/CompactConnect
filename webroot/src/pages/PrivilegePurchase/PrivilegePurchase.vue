<!--
    PrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 1/31/2025.
-->

<template>
    <div class="purchase-flow-container">
        <ProgressBar :progressPercent="progressPercent" />
        <PrivilegePurchaseInformationConfirmation
            v-if="isConfirmInfoRoute"
            :flowStep="currentFlowStep"
            class="step"
        />
        <PrivilegePurchaseSelect
            v-if="isSelectPrivilegesRoute"
            :flowStep="currentFlowStep"
            class="step"
        />
        <PrivilegePurchaseAttestation
            v-if="isAttestationRoute"
            :flowStep="currentFlowStep"
            class="step"
        />
        <PrivilegePurchaseFinalize
            v-if="isFinalizeRoute"
            :flowStep="currentFlowStep"
            class="step"
        />
        <PrivilegePurchaseSuccessful
            v-if="isPurchaseSuccessfulRoute"
            :flowStep="currentFlowStep"
            class="step"
        />
    </div>
</template>

<script lang="ts" src="./PrivilegePurchase.ts"></script>
<style scoped lang="less" src="./PrivilegePurchase.less"></style>
