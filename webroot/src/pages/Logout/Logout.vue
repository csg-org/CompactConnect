<!--
    Logout.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="logout-container">
        <div class="message">{{ $t('common.loggingOut') }}</div>
        <LoadingSpinner :noBgColor="true" />
    </div>
</template>

<script lang="ts" src="./Logout.ts"></script>
<style scoped lang="less" src="./Logout.less"></style>
