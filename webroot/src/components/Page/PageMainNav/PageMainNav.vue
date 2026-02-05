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
        @mouseenter="!isMenuTouchToggle && navExpand($event)"
        @focusin="!isMenuTouchToggle && navExpand()"
        @mouseleave="!isMenuTouchToggle && navCollapse($event)"
        @focusout="!isMenuTouchToggle && navCollapse()"
        v-click-outside="clickOutside"
    >
        <div v-if="$matches.tablet.min && !isMenuTouchToggle" class="logo-container">
            <img
                src="@assets/logos/compact-connect-logo-white.svg"
                :alt="$t('common.appName')"
                class="logo"
                @click="logoClick"
                @keyup.enter="logoClick"
                role="button"
                :aria-label="$t('common.appName')"
                tabindex="0"
            />
        </div>
        <ul class="nav main-nav">
            <li v-for="link in mainLinks" :key="link.label" class="page-nav main-links">
                <!-- Internal links that should only have active style if the route path matches exactly -->
                <router-link v-if="!link.isExternal && link.isExactActive"
                    :to="{ name: link.to, params: link.params || {}}"
                    exact
                    :aria-label="link.label"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- All other internal links -->
                <router-link v-else-if="!link.isExternal"
                    :to="{ name: link.to, params: link.params || {}}"
                    :aria-label="link.label"
                    tabindex="0"
                    :class="{ 'router-link-active': link.isActive }"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- External links (to another domain) -->
                <a v-else
                    :href="link.to"
                    class="external-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    :aria-label="link.label"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </a>
            </li>
        </ul>
        <div class="compact-selector">
            <CompactSelector
                v-if="isLoggedInAsStaff && isNavExpanded"
                :isPermissionBased="true"
                :hideIfNotMultiple="true"
            />
        </div>
        <div v-if="$store.state.isAppModeDisplayed" class="app-mode">
            App mode: {{ $store.state.appMode }}
        </div>
        <div v-if="isLoggedIn" class="separator"></div>
        <ul
            class="nav my-nav"
            :class="{
                'touch-device': isTouchDevice,
                'iphone-safari': isIphoneSafari,
            }"
        >
            <li v-for="link in myLinks" :key="link.label" class="page-nav my-links">
                <!-- Internal links that should only have active style if the route path matches exactly -->
                <router-link v-if="!link.isExternal && link.isExactActive"
                    :to="{ name: link.to, params: link.params || {}}"
                    exact
                    :aria-label="link.label"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- All other internal links -->
                <router-link v-else-if="!link.isExternal"
                    :to="{ name: link.to, params: link.params || {}}"
                    :aria-label="link.label"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </router-link>
                <!-- External links (to another domain) -->
                <a v-else
                    :href="link.to"
                    class="external-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    :aria-label="link.label"
                    tabindex="0"
                >
                    <component v-if="link.iconComponent" :is="link.iconComponent" class="link-icon" />
                    <span v-if="isNavExpanded" class="link-label">{{ link.label }}</span>
                </a>
            </li>
        </ul>
    </div>
</template>

<script lang="ts" src="./PageMainNav.ts"></script>
<style scoped lang="less" src="./PageMainNav.less"></style>
