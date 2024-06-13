<!--
    PageHeader.vue
    inHere

    Created by InspiringApps on 5/4/2020.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div class="page-header">
        <div class="header-content">{{ $t('styleGuide.headerPlaceholder') }}</div>
        <div class="nav-container">
            <PageNav />
        </div>
    </div>
</template>

<script lang="ts" src="./PageHeader.ts"></script>
<style scoped lang="less" src="./PageHeader.less"></style>
