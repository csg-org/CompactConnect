<!--
    CompactSettings.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Section class="compact-settings-container">
        <h1 class="compact-settings-title">{{ $t('compact.settingsTitle') }}</h1>
        <PaymentProcessorConfig />
    </Section>
</template>

<script lang="ts" src="./CompactSettings.ts"></script>
<style scoped lang="less" src="./CompactSettings.less"></style>
