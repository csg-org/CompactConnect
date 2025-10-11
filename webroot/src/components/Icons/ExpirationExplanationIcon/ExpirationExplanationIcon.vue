<!--
    ExpirationExplanationIcon.vue
    CompactConnect

    Created by InspiringApps on 9/15/2025.
-->

<template>
    <div class="expiration-icon-container">
        <div v-if="isCollapsibleExplanation" class="clock-button-wrapper" v-click-outside="hideExpirationExplanation">
            <div class="clock-logo-container">
                <img
                    role="button"
                    tabindex="0"
                    class="clock-logo-img"
                    src="@assets/icons/ico-clock.svg"
                    :alt="$t('licensing.privilegeExpirationIcon')"
                    aria-label="toggle expiration explanation"
                    :aria-describedby="(shouldShowExpirationExplanation) ? 'expiration-explanation' : undefined"
                    :aria-expanded="shouldShowExpirationExplanation"
                    @click="toggleExpirationExplanation"
                    @keyup.enter="toggleExpirationExplanation"
                />
            </div>
            <Transition name="fade" :mode="elementTransitionMode">
                <div
                    v-if="shouldShowExpirationExplanation"
                    class="collapsible-expiration-explanation-wrapper"
                >
                    <div class="triangle" />
                    <div
                        id="expiration-explanation"
                        class="expiration-explanation"
                        v-html="$t('licensing.expirationTimeExplanation')"
                    />
                </div>
            </Transition>
        </div>
        <div v-else class="clock-img-wrapper">
            <div class="clock-logo-container">
                <img
                    class="clock-logo-img"
                    src="@assets/icons/ico-clock.svg"
                    :alt="$t('licensing.privilegeExpirationIcon')"
                />
            </div>
            <div v-html="$t('licensing.expirationTimeExplanation')" class="expiration-explanation"/>
        </div>
    </div>
</template>

<script lang="ts" src="./ExpirationExplanationIcon.ts"></script>
<style scoped lang="less" src="./ExpirationExplanationIcon.less"></style>
