<!--
    CollapseCaretButton.vue
    CompactConnect

    Created by InspiringApps on 11/3/2024.
-->

<template>
    <div
        @click="toggleCollapse"
        @keydown.prevent="toggleCollapse"
        tabIndex="0"
        class="collapse-caret-button"
    >
        <img v-if="isUp" class="caret-img" src="@assets/icons/up-caret.svg" alt="Collapse Button Logo" />
        <img v-else class="caret-img" src="@assets/icons/down-caret.svg" alt="Expand Button Logo" />
    </div>
</template>

<script lang="ts" src="./CollapseCaretButton.ts"></script>
<style scoped lang="less" src="./CollapseCaretButton.less"></style>
