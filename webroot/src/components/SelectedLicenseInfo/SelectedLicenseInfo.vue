<!--
    SelectedLicenseInfo.vue
    CompactConnect

    Created by InspiringApps on 3/7/2025.
-->

<template>
    <div class="selected-license-info-container">
        <div class="title-row">{{license.displayName()}}</div>
        <div class="expiration-row">{{expirationDisplay}}</div>
    </div>
</template>

<script lang="ts" src="./SelectedLicenseInfo.ts"></script>
<style scoped lang="less" src="./SelectedLicenseInfo.less"></style>
