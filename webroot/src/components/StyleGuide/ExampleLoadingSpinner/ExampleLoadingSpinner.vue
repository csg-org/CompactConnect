<!--
    ExampleLoadingSpinner.vue
    InspiringApps modules

    Created by InspiringApps on 5/5/2021.
-->

<template>
    <Section class="example-loading-spinner-section">
        <h2>Example Loading Spinner</h2>
        <InputButton :label="$t('styleGuide.showSpinner')" @click="showSpinner" />
    </Section>
</template>

<script lang="ts" src="./ExampleLoadingSpinner.ts"></script>
<style scoped lang="less" src="./ExampleLoadingSpinner.less"></style>
