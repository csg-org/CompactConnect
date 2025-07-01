<!--
    CompactSettings.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Section class="compact-settings-container">
        <h1 v-if="isCompactAdmin || shouldShowStateList" class="compact-settings-title">
            {{ $t('compact.settingsTitle') }}
        </h1>
        <CompactSettingsConfig v-if="isCompactAdmin" class="section compact-config" />
        <PaymentProcessorConfig v-if="isCompactAdmin" class="section payment-config" />
        <StateSettingsList v-if="shouldShowStateList" class="section state-list" />
    </Section>
</template>

<script lang="ts" src="./CompactSettings.ts"></script>
<style scoped lang="less" src="./CompactSettings.less"></style>
