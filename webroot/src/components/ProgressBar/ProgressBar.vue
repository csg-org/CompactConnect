<!--
    ProgressBar.vue
    CompactConnect

    Created by InspiringApps on 2/3/2025.
-->

<template>
    <div class="progress-bar">
        <div class="finished-portion" :style="{ width: progressPercent + '%'}" />
        <div class="unifinished-portion" :style="{ width: remainingPercent + '%'}"/>
    </div>
</template>

<script lang="ts" src="./ProgressBar.ts"></script>
<style scoped lang="less" src="./ProgressBar.less"></style>
