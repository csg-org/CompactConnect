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
        {{ $t('styleGuide.mockPopulate') }}
    </div>
</template>

<script lang="ts" src="./MockPopulate.ts"></script>
<style scoped lang="less" src="./MockPopulate.less"></style>
