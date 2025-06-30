<!--
    CompactSettings.vue
    CompactConnect

    Created by InspiringApps on 12/5/2024.
-->

<template>
    <Section class="compact-settings-container">
        <h1 v-if="isCompactAdmin || shouldShowStateList" class="compact-settings-title">
            {{ $t('compact.settingsTitle') }}
        </h1>
        <CompactSettingsConfig v-if="isCompactAdmin" class="section compact-config" />
        <PaymentProcessorConfig v-if="isCompactAdmin" class="section payment-config" />
        <div v-if="shouldShowStateList" class="section state-list">
            <LoadingSpinner v-if="this.isCompactConfigLoading" />
            <div v-if="compactConfigLoadingErrorMessage" class="compact-loading-error">
                {{ compactConfigLoadingErrorMessage }}
            </div>
            <div v-if="$matches.desktop.min" class="state-row header-row">
                <div class="state-cell header-cell state">{{ $t('common.state') }}</div>
                <div
                    v-if="compactConfigStates.length"
                    class="state-cell header-cell actions compact-enable"
                    :class="{ 'is-last-column': !isStateAdminAny }"
                >
                    {{ $t('common.status') }}
                </div>
                <div v-if="isStateAdminAny" class="state-cell header-cell actions state-edit">
                    {{ $t('compact.configuration') }}
                </div>
            </div>
            <div
                v-for="(rowPermission, index) in stateConfigRowPermissions"
                :key="`state-row-${index + 1}`"
                class="state-row"
            >
                <div class="state-cell state">{{ rowPermission.state.name() }}</div>
                <div
                    v-if="compactConfigStates.length"
                    class="state-cell actions compact-enable"
                    :class="{ 'is-last-column': !isStateAdminAny }"
                >
                    <button
                        v-if="rowPermission.isCompactAdmin && !rowPermission.isLiveForCompact"
                        class="state-action-btn transparent"
                        @click="() => console.log('show confirmation modal')"
                    >
                        {{ $t('compact.enable')}}
                    </button>
                    <div v-else-if="rowPermission.isCompactAdmin" class="state-status">{{ $t('compact.live')}}</div>
                </div>
                <div v-if="isStateAdminAny" class="state-cell actions state-edit">
                    <button
                        v-if="rowPermission.isStateAdmin"
                        class="state-action-btn transparent"
                        @click="routeToStateConfig(rowPermission.state.abbrev)"
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
