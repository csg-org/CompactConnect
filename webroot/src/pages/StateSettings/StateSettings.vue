<!--
    StateSettings.vue
    CompactConnect

    Created by InspiringApps on 5/20/2025.
-->

<template>
    <Section class="state-settings-container">
        <InputButton
            :label="$t('common.back').toUpperCase()"
            :aria-label="$t('common.back')"
            :isTextLike="true"
            :shouldHideMargin="true"
            class="back-btn"
            @click="goBack"
        />
        <h1 class="state-settings-title">{{ pageTitle }}</h1>
        <StateSettingsConfig
            v-if="isStateAdmin"
            :stateAbbrev="stateAbbrev"
            class="state-config"
        />
    </Section>
</template>

<script lang="ts" src="./StateSettings.ts"></script>
<style scoped lang="less" src="./StateSettings.less"></style>
