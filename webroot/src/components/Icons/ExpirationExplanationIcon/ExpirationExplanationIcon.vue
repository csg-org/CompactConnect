<!--
    ExpirationExplanationIcon.vue
    CompactConnect

    Created by InspiringApps on 9/15/2025.
-->

<template>
    <div class="clock-logo-wrapper">
        <div class="clock-logo-container">
            <img
                role="button"
                tabindex="0"
                class="clock-logo-img"
                src="@assets/icons/ico-clock.svg"
                :alt="$t('licensing.privilegeExpirationIcon')"
                @click="toggleExpirationExplanation"
                @keyup.enter="toggleExpirationExplanation"
            />
        </div>
        <Transition name="fade" :mode="elementTransitionMode">
            <div v-if="shouldShowExpirationExplanation" class="expiration-explanation-wrapper">
                <div class="triangle" />
                <div v-html="$t('licensing.expirationTimeExplanation')" class="expiration-explanation"/>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts" src="./ExpirationExplanationIcon.ts"></script>
<style scoped lang="less" src="./ExpirationExplanationIcon.less"></style>
