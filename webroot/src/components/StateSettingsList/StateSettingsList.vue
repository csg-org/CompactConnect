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
                :title="$t('compact.confirmSaveStateTitle')"
                :showActions="false"
                @keydown.tab="focusTrapStateLiveModal($event)"
                @keyup.esc="closeStateLiveModal"
            >
                <template v-slot:content>
                    <div class="modal-content confirm-modal-content">
                        <span v-if="isCompactSeparatingPrivilegeEnabled && !getStateConfigIsLive()">
                            {{ $t('compact.privilegePurchaseEnabledSubtextMultiState3', {
                                state: getSelectedStateName()
                            }) }}
                        </span>
                        {{ $t('common.cannotBeUndone') }}
                        <form class="confirm-state-live-form" @submit.prevent="submitStateLive">
                            <div
                                v-if="isCompactSeparatingPrivilegeEnabled"
                                class="confirm-state-form-input-container"
                            >
                                <template v-if="isStateConfigAdverseActionEmailMissing()">
                                    <MockPopulate
                                        v-if="isMockPopulateEnabled"
                                        :isEnabled="isMockPopulateEnabled"
                                        @selected="mockPopulate"
                                    />
                                    <InputEmailList :formInput="formData.adverseActionNotificationEmails" />
                                    <button
                                        class="btn-catch-email-lists"
                                        @click.stop.prevent="() => null"
                                        tabindex="-1"
                                    >+</button>
                                </template>
                                <div v-else class="state-email-list">
                                    <div class="state-email-list-label">
                                        {{ $t('compact.adverseActionsNotificationEmails') }}:
                                    </div>
                                    <div
                                        v-for="(email, index) in getStateConfigAdverseActionEmails()"
                                        :key="index"
                                        class="state-email"
                                    >
                                        {{ email }}
                                    </div>
                                </div>
                            </div>
                        </form>
                        <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
                        <div class="action-button-row">
                            <InputSubmit
                                id="confirm-modal-submit-button"
                                class="action-button submit-button continue-button"
                                :formInput="formData.stateLiveModalContinue"
                                @click="submitStateLive"
                                :label="(isFormLoading)
                                    ? $t('common.loading')
                                    : getStateLiveModalSubmitLabel()"
                                :isTransparent="true"
                                :isEnabled="isFormValid && !isFormLoading"
                            />
                            <InputButton
                                id="confirm-modal-cancel-button"
                                class="action-button cancel-button"
                                :label="$t('common.cancel')"
                                :onClick="closeStateLiveModal"
                                :isWarning="true"
                                :isEnabled="!isFormLoading"
                            />
                        </div>
                    </div>
                </template>
            </Modal>
        </TransitionGroup>
    </div>
</template>

<script lang="ts" src="./StateSettingsList.ts"></script>
<style scoped lang="less" src="./StateSettingsList.less"></style>
