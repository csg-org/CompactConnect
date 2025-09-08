<!--
    StateSettingsList.vue
    CompactConnect

    Created by InspiringApps on 7/1/2025.
-->

<template>
    <div class="state-config-list-container">
        <LoadingSpinner v-if="isLoading" />
        <div v-if="loadingErrorMessage" class="compact-loading-error">{{ loadingErrorMessage }}</div>
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
                    @click="toggleStateLiveModal(rowPermission.state)"
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
        <TransitionGroup>
            <Modal
                v-if="isStateLiveModalDisplayed"
                modalId="confirm-state-live-modal"
                class="confirm-config-modal"
                :title="$t('compact.confirmSaveCompactTitle')"
                :showActions="true"
                @keydown.tab="focusTrapStateLiveModal($event)"
                @keyup.esc="closeStateLiveModal"
            >
                <template v-slot:content>
                    <div class="modal-content confirm-modal-content">
                        {{ $t('common.cannotBeUndone') }}
                        <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
                    </div>
                </template>
                <template v-slot:actions>
                    <div class="action-button-row">
                        <InputButton
                            id="confirm-modal-submit-button"
                            @click="submitStateLive"
                            class="action-button submit-button continue-button"
                            :label="(isFormLoading)
                                ? $t('common.loading')
                                : $t('compact.confirmSaveCompactYes')"
                            :isTransparent="true"
                            :isEnabled="!isFormLoading"
                        />
                        <InputButton
                            id="confirm-modal-cancel-button"
                            class="action-button cancel-button"
                            :label="$t('common.cancel')"
                            :isWarning="true"
                            :isEnabled="isFormValid && !isFormLoading"
                            :onClick="closeStateLiveModal"
                        />
                    </div>
                </template>
            </Modal>
        </TransitionGroup>
    </div>
</template>

<script lang="ts" src="./StateSettingsList.ts"></script>
<style scoped lang="less" src="./StateSettingsList.less"></style>
