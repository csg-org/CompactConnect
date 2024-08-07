<!--
    CompactToggle.vue
    inHere

    Created by InspiringApps on 6/10/2020.
-->

<template>
    <div class="compact-toggle-container">
        <div
            class="compact-toggle compact-off"
            :class="{ 'active': !isCompact }"
            @click="toggleMode(false)"
            @keyup.enter="toggleMode(false)"
        >
            <svg
                class="ico ico-compact-off"
                version="1.1" x="0px" y="0px"
                viewBox="0 0 17 14"
                xml:space="preserve"
            >
                <path d="M0,9h4V5H0V9z M0,14h4v-4H0V14z M0,4h4V0H0V4z M5,9h12V5H5V9z M5,14h12v-4H5V14z M5,0v4h12V0H5z"/>
            </svg>
        </div>
        <div
            class="compact-toggle compact-on"
            :class="{ 'active': isCompact }"
            @click="toggleMode(true)"
            @keyup.enter="toggleMode(true)"
        >
            <svg
                class="ico ico-compact-on"
                x="0px" y="0px"
                viewBox="0 0 17 14"
                xml:space="preserve"
            >
            <path d="M0,0h17v2H0V0z M0,3h17v2H0V3z M0,6h17v2H0V6z M0,9h17v2H0V9z M0,12h17v2H0V12z"/>
            </svg>
        </div>
        <span class="break"></span>
    </div>
</template>

<script lang="ts" src="./CompactToggle.ts"></script>
<style scoped lang="less" src="./CompactToggle.less"></style>
