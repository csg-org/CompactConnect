<!--
    PrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 1/31/2025.
-->

<template>
    <div>
        <PrivilegePurchaseInformationConfirmation
            v-if="isConfirmInfoRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        />
        <PrivilegePurchaseSelect
            v-if="isSelectPrivilegesRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        />
        <PrivilegePurchaseAttestation
            v-if="isAttestationRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        />
        <PrivilegePurchaseFinalize
            v-if="isFinalizeRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        />
        <PrivilegePurchaseSuccessful
            v-if="isPurchaseSuccessfulRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        />
    </div>
</template>

<script lang="ts" src="./PrivilegePurchase.ts"></script>
<style scoped lang="less" src="./PrivilegePurchase.less"></style>
