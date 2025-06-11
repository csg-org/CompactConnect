<!--
    PageContainer.vue
    inHere

    Created by InspiringApps on 5/4/2020.
-->

<template>
    <div class="page-container" :class="{
        'no-top-pad': !shouldPadTop,
        'no-page-header': !includePageHeader
    }">
        <header>
            <PageHeader v-if="includePageHeader"></PageHeader>
        </header>
        <PageNav v-if="includeMainNav" />
        <div class="page-content" :class="{ 'include-nav': includeMainNav }" role="main">
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
