<!--
    MockPopulate.vue
    CompactConnect

    Created by InspiringApps on 6/20/2024.
-->

<template>
    <div
        v-if="isEnabled"
        @click="clicked"
        @keyup.enter="clicked"
        class="mock-populate"
    >
        <template v-if="customLabel">{{ customLabel }}</template>
        <template v-else>{{ $t('styleGuide.mockPopulate') }}</template>
    </div>
</template>

<script lang="ts" src="./MockPopulate.ts"></script>
<style scoped lang="less" src="./MockPopulate.less"></style>
