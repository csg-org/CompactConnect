<!--
    StateSettingsConfig.vue
    CompactConnect

    Created by InspiringApps on 5/13/2025.
-->

<template>
    <Card class="state-config">
        <div v-if="isLoading" class="loading-container"><LoadingSpinner /></div>
        <div v-else-if="loadingErrorMessage" class="loading-error-container">
            <div class="general-message">{{ $t('compact.configLoadingErrorState') }}</div>
            <div class="response-message">{{ loadingErrorMessage }}</div>
        </div>
        <form v-else class="state-config-form" @submit.prevent="handleSubmit(false)">
            <div class="state-config-form-container">
                <!-- Privilege fees -->
                <h2 class="form-section-title fees">{{ $t('compact.privilegeFees') }}</h2>
                <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                <InputText
                    v-for="(formInput) in feeInputs"
                    :key="formInput.id"
                    :formInput="formInput"
                    class="form-row currency"
                    @input="formatInput(formInput)"
                    @blur="formatBlur(formInput, formInput.id.endsWith('military'))"
                />
                <!-- Jurisprudence -->
                <h2 class="form-section-title jurisprudence">{{ $t('compact.jurisprudence') }}</h2>
                <InputRadioGroup :formInput="formData.isJurisprudenceExamRequired" class="form-row" />
                <InputText :formInput="formData.jurisprudenceInfoLink" class="form-row jurisprudence-info-link" />
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
                    :formInput="formData.isPurchaseEnabled"
                    class="live-status-radio form-row"
                    @blur="populateMissingPurchaseEnabled"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                    class="state-config-submit"
                />
            </div>
        </form>
        <TransitionGroup>
            <Modal
                v-if="isConfirmConfigModalDisplayed"
                modalId="confirm-state-config-modal"
                class="confirm-config-modal"
                :title="$t('compact.confirmSaveCompactTitle')"
                :showActions="true"
                @keydown.tab="focusTrapConfirmConfigModal($event)"
                @keyup.esc="closeConfirmConfigModal"
            >
                <template v-slot:content>
                    <div class="modal-content confirm-modal-content">
                        {{ $t('common.cannotBeUndone') }}
                    </div>
                </template>
                <template v-slot:actions>
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
                </template>
            </Modal>
        </TransitionGroup>
    </Card>
</template>

<script lang="ts" src="./StateSettingsConfig.ts"></script>
<style scoped lang="less" src="./StateSettingsConfig.less"></style>
