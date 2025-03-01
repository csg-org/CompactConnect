<!--
    CollapseCaretButton.vue
    CompactConnect

    Created by InspiringApps on 11/3/2024.
-->

<template>
    <div
        @click="toggleCollapse"
        @keyup.enter="toggleCollapse"
        tabIndex="0"
        class="collapse-caret-button"
    >
        <svg
            v-if="isUp" viewBox="0 0 24 14" role="img"
            fill="none">
            <title>Collapse Button Logo</title>
            <path d="M2 11.6342L11.9054 1.72852L21.8111 11.6342"
            stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <svg v-else
            viewBox="0 0 24 14" fill="none">
            <title>Expand Button Logo</title>
            <path d="M21.811 1.7271L11.9056 11.6328L1.99991 1.7271"
            stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    </div>
</template>

<script lang="ts" src="./CollapseCaretButton.ts"></script>
<style scoped lang="less" src="./CollapseCaretButton.less"></style>
