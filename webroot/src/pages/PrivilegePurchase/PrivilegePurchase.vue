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
        >
            <template v-slot:progress-bar>
                <ProgressBar :progressPercent="progressPercent" />
            </template>
        </PrivilegePurchaseInformationConfirmation>
        <PrivilegePurchaseSelect
            v-if="isSelectPrivilegesRoute"
            :flowStep="currentFlowStep"
            :progressPercent="progressPercent"
        >
            <template v-slot:progress-bar>
                <ProgressBar :progressPercent="progressPercent" />
            </template>
        </PrivilegePurchaseSelect>
        <PrivilegePurchaseAttestation
            v-if="isAttestationRoute"
            :flowStep="currentFlowStep"
        >
            <template v-slot:progress-bar>
                <ProgressBar :progressPercent="progressPercent" />
            </template>
        </PrivilegePurchaseAttestation>
        <PrivilegePurchaseFinalize
            v-if="isFinalizeRoute"
            :flowStep="currentFlowStep"
        >
            <template v-slot:progress-bar>
                <ProgressBar :progressPercent="progressPercent" />
            </template>
        </PrivilegePurchaseFinalize>
        <PrivilegePurchaseSuccessful
            v-if="isPurchaseSuccessfulRoute"
            :flowStep="currentFlowStep"
        >
            <template v-slot:progress-bar>
                <ProgressBar :progressPercent="progressPercent" />
            </template>
        </PrivilegePurchaseSuccessful>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchase.ts"></script>
<style scoped lang="less" src="./PrivilegePurchase.less"></style>
