<!--
    MobileStoreLinks.vue
    InspiringApps modules

    Created by InspiringApps on 9/4/2020.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div class="download-link-container">
        <a :href="appleStoreLink" target="_blank" class="download-link apple">
            <img
                v-lazy="require('@assets/images/app-download/apple/app-store-badge@2x.png')"
                alt="Download on the Apple App Store"
            />
        </a>
        <a
            :href="googleStoreLink"
            target="_blank"
            class="download-link google"
        >
            <img
                v-lazy="require('@assets/images/app-download/google/google-play-badge-cropped@2x.png')"
                alt="Download on Google Play"
            />
        </a>
    </div>
</template>

<script lang="ts" src="./MobileStoreLinks.ts"></script>
<style scoped lang="less" src="./MobileStoreLinks.less"></style>
