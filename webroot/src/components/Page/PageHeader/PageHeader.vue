<!--
    PageHeader.vue
    inHere

    Created by InspiringApps on 5/4/2020.
-->

<template>
    <div class="page-header-container">
        <div v-if="$matches.phone.only" class="logo-container">
            <img
                src="@assets/logos/compact-connect-logo-white.svg"
                :alt="$t('common.appName')"
                class="logo"
                @click="logoClick"
                @keyup.enter="logoClick"
                role="button"
                tabindex="0"
            />
        </div>
        <div v-if="$matches.phone.only" class="nav-toggle-container">
            <div
                class="nav-toggle"
                @click="navToggle"
                @keyup.enter="navToggle"
                role="button"
                tabindex="0"
                :aria-label="$t('common.toggleNav')"
            >
                X
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PageHeader.ts"></script>
<style scoped lang="less" src="./PageHeader.less"></style>
