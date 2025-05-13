<!--
    CompactSettings.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Section class="compact-settings-container">
        <h1 class="compact-settings-title">{{ $t('compact.settingsTitle') }}</h1>
        <PaymentProcessorConfig v-if="isCompactAdmin" class="section payment-config" />
        <CompactSettingsConfig v-if="isCompactAdmin" class="section compact-config" />
    </Section>
</template>

<script lang="ts" src="./CompactSettings.ts"></script>
<style scoped lang="less" src="./CompactSettings.less"></style>
