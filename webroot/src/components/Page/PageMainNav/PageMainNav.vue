<!--
    PageMainNav.vue
    inHere

    Created by InspiringApps on 11/20/2020.
-->

<template>
    <div v-if="mainLinks.length" class="main-nav-container" v-click-outside="collapseMainNav">
        <div v-if="isMobile" class="nav-toggle" @click="toggleMainNav" @keyup.enter="toggleMainNav">
            <div></div>
            <div></div>
            <div></div>
        </div>
        <transition name="nav-slide">
            <ul v-if="isMainNavVisible" class="main-nav" @click="toggleMainNav" @keyup.enter="toggleMainNav">
                <li v-for="link in mainLinks" :key="link.label" class="page-nav main-links">
                    <!-- Internal links that should only have active style if the route path matches exactly -->
                    <router-link v-if="!link.isExternal && link.isExactActive"
                        :to="{ name: link.to, params: link.params || {}}"
                        exact
                    >
                        {{ link.label }}
                    </router-link>
                    <!-- All other internal links -->
                    <router-link v-else-if="!link.isExternal"
                        :to="{ name: link.to, params: link.params || {}}"
                    >
                        {{ link.label }}
                    </router-link>
                    <!-- External links (to another domain) -->
                    <a v-else
                        :href="link.to"
                        class="external-link"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        {{ link.label }}
                    </a>
                </li>
            </ul>
        </transition>
    </div>
</template>

<script lang="ts" src="./PageMainNav.ts"></script>
<style scoped lang="less" src="./PageMainNav.less"></style>
