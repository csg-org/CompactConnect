<!--
    CompactSettings.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Section class="compact-settings-container">
        <h1 class="compact-settings-title">{{ $t('compact.settingsTitle') }}</h1>
        <PaymentProcessorConfig v-if="isCompactAdmin" class="section payment-config" />
        <CompactSettingsConfig v-if="isCompactAdmin" class="section compact-config" />
        <div v-if="isStateAdminMultiple" class="state-list">
            <div class="state-row header-row">
                <div class="state-cell header-cell state">{{ $t('common.state') }}</div>
                <div class="state-cell header-cell actions">{{ $t('compact.configuration') }}</div>
            </div>
            <div
                v-for="(statePermission, index) in statePermissionsAdmin"
                :key="`state-row-${index + 1}`"
                class="state-row"
            >
                <div class="state-cell state">{{ statePermission.state.name() }}</div>
                <div class="state-cell actions">
                    <button
                        class="transparent"
                        @click="routeToStateConfig(statePermission.state.abbrev)"
                    >
                        {{ $t('common.edit')}}
                    </button>
                </div>
            </div>
        </div>
    </Section>
</template>

<script lang="ts" src="./CompactSettings.ts"></script>
<style scoped lang="less" src="./CompactSettings.less"></style>
