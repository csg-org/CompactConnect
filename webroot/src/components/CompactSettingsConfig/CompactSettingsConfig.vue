<!--
    CompactSettingsConfig.vue
    CompactConnect

    Created by InspiringApps on 5/13/2025.
-->

<template>
    <Card class="compact-config">
        <div v-if="isLoading" class="loading-container"><LoadingSpinner /></div>
        <div v-else-if="loadingErrorMessage" class="loading-error-container">
            <div class="general-message">{{ $t('compact.configLoadingErrorCompact') }}</div>
            <div class="response-message">{{ loadingErrorMessage }}</div>
        </div>
        <form v-else class="compact-config-form" @submit.prevent="handleSubmit(false)">
            <div class="compact-config-form-container">
                <!-- Privilege fees -->
                <h2 class="form-section-title fees">{{ $t('compact.privilegeFees') }}</h2>
                <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                <InputText
                    :formInput="formData.compactFee"
                    class="form-row currency"
                    @input="formatInput(formData.compactFee)"
                    @blur="formatBlur(formData.compactFee)"
                />
                <InputText
                    :formInput="formData.creditCardTransactionFee"
                    class="form-row currency"
                    @input="formatInput(formData.creditCardTransactionFee)"
                    @blur="formatBlur(formData.creditCardTransactionFee, true)"
                />
                <!-- Notifications -->
                <h2 class="form-section-title notifications">{{ $t('compact.notifications') }}</h2>
                <InputEmailList :formInput="formData.opsNotificationEmails" />
                <InputEmailList :formInput="formData.adverseActionNotificationEmails" />
                <InputEmailList :formInput="formData.summaryReportNotificationEmails" />
                <button
                    class="btn-catch-email-lists"
                    @click.stop.prevent="() => null"
                    tabindex="-1"
                >+</button>
                <!-- Live status -->
                <h2 class="form-section-title live-status">{{ $t('compact.licenseRegistrationTitle') }}</h2>
                <InputRadioGroup
                    :formInput="formData.isRegistrationEnabled"
                    class="live-status-radio form-row"
                    @blur="populateMissingRegistrationEnabled"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                    class="compact-config-submit"
                />
            </div>
        </form>
        <TransitionGroup>
            <Modal
                v-if="isConfirmConfigModalDisplayed"
                modalId="confirm-config-modal"
                class="confirm-config-modal"
                :title="$t('compact.confirmSaveCompactTitle')"
                :showActions="false"
                @keydown.tab="focusTrapConfirmConfigModal($event)"
                @keyup.esc="closeConfirmConfigModal"
            >
                <template v-slot:content>
                    <div class="modal-content confirm-modal-content">
                        {{ $t('common.cannotBeUndone') }}
                        <div class="action-button-row">
                            <InputButton
                                id="confirm-modal-submit-button"
                                @click="submitConfirmConfigModal"
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
                                :onClick="closeConfirmConfigModal"
                            />
                        </div>
                    </div>
                </template>
            </Modal>
        </TransitionGroup>
    </Card>
</template>

<script lang="ts" src="./CompactSettingsConfig.ts"></script>
<style scoped lang="less" src="./CompactSettingsConfig.less"></style>
