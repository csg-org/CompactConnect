<!--
    LoadingSpinner.vue
    inHere

    Created by InspiringApps on 5/28/2020.
-->

<template>
    <div class="loading-spinner">
        <div class="loading-spinner-mask" :class="{ 'no-bg-color': noBgColor }"></div>
        <div class="loading-spinner-container">
            <div class="spinner"></div>
        </div>
    </div>
</template>

<script lang="ts" src="./LoadingSpinner.ts"></script>
<style scoped lang="less" src="./LoadingSpinner.less"></style>
