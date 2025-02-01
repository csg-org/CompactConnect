<!--
    PrivilegePurchase.vue
    CompactConnect

    Created by InspiringApps on 1/31/2025.
-->

<template>
    <div>
        <PrivilegePurchaseSelect v-if="isSelectPrivilegesRoute" />
        <PrivilegePurchaseAttestation v-if="isAttestationRoute" />
        <PrivilegePurchaseFinalize v-if="isFinalizeRoute" />
        <PrivilegePurchaseSuccessful v-if="isPurchaseSuccessfulRoute" />
    </div>
</template>

<script lang="ts" src="./PrivilegePurchase.ts"></script>
<style scoped lang="less" src="./PrivilegePurchase.less"></style>
