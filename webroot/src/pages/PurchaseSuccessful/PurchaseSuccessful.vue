<!--
    PurchaseSuccessful.vue
    CompactConnect

    Created by InspiringApps on 11/5/2024.
-->

<template>
    <div class="purchase-success-container">
        <div class="purchase-success-core">
            <div class="purchase-success-title">
                {{purchaseSuccessfulTitle}}
            </div>
            <div class="purchase-success-content">
                {{purchaseSuccessfulMessage}}
            </div>
        </div>
        <div class="button-row">
            <InputButton
                :label="finishText"
                aria-label="finish"
                class="finish-button"
                @click="handleFinishClicked"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./PurchaseSuccessful.ts"></script>
<style scoped lang="less" src="./PurchaseSuccessful.less"></style>
