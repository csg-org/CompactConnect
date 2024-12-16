<!--
    PageMainNav.vue
    inHere

    Created by InspiringApps on 11/20/2020.
-->

<template>
    <div
        v-if="mainLinks.length"
        class="main-nav-container"
        :class="{ expanded: isNavExpanded }"
        @mouseenter="!$matches.phone.only && navExpand($event)"
        @focusin="!$matches.phone.only && navExpand()"
        @mouseleave="!$matches.phone.only && navCollapse($event)"
        @focusout="!$matches.phone.only && navCollapse()"
    >
        <div v-if="$matches.tablet.min" class="logo-container">
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
        <ul class="nav main-nav">
            <li v-for="link in mainLinks" :key="link.label" class="page-nav main-links">
                <!-- Internal links that should only have active style if the route path matches exactly -->
                <router-link v-if="!link.isExternal && link.isExactActive"
                    :to="{ name: link.to, params: link.params || {}}"
                    exact
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- All other internal links -->
                <router-link v-else-if="!link.isExternal"
                    :to="{ name: link.to, params: link.params || {}}"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- External links (to another domain) -->
                <a v-else
                    :href="link.to"
                    class="external-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </a>
            </li>
        </ul>
        <div class="separator"></div>
        <ul class="nav my-nav">
            <li v-for="link in myLinks" :key="link.label" class="page-nav my-links">
                <!-- Internal links that should only have active style if the route path matches exactly -->
                <router-link v-if="!link.isExternal && link.isExactActive"
                    :to="{ name: link.to, params: link.params || {}}"
                    exact
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- All other internal links -->
                <router-link v-else-if="!link.isExternal"
                    :to="{ name: link.to, params: link.params || {}}"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- External links (to another domain) -->
                <a v-else
                    :href="link.to"
                    class="external-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" />
                    <span v-if="globalStore.isNavExpanded" class="link-label">{{ link.label }}</span>
                </a>
            </li>
        </ul>
    </div>
</template>

<script lang="ts" src="./PageMainNav.ts"></script>
<style scoped lang="less" src="./PageMainNav.less"></style>
