<!--
    PageContainer.vue
    inHere

    Created by InspiringApps on 5/4/2020.
-->

<template>
    <div class="page-container">
        <header>
            <PageHeader v-if="includePageHeader"></PageHeader>
        </header>
        <PageNav />
        <div class="page-content" role="main">
            <transition name="fade">
                <PageLoadingMask v-show="isLoading"></PageLoadingMask>
            </transition>
            <slot></slot>
        </div>
        <PageFooter v-if="includePageFooter"></PageFooter>
    </div>
</template>

<script lang="ts" src="./PageContainer.ts"></script>
<style scoped lang="less" src="./PageContainer.less"></style>
