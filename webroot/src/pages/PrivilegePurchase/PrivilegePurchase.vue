<!--
    PrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 1/31/2025.
-->

<template>
    <div>
        <PrivilegePurchaseInformationConfirmation v-if="isConfirmInfoRoute" :flowStep=1 />
        <PrivilegePurchaseSelect v-if="isSelectPrivilegesRoute" :flowStep=2 />
        <PrivilegePurchaseAttestation v-if="isAttestationRoute" :flowStep=3 />
        <PrivilegePurchaseFinalize v-if="isFinalizeRoute" :flowStep=4 />
        <PrivilegePurchaseSuccessful v-if="isPurchaseSuccessfulRoute" :flowStep=5 />
    </div>
</template>

<script lang="ts" src="./PrivilegePurchase.ts"></script>
<style scoped lang="less" src="./PrivilegePurchase.less"></style>
