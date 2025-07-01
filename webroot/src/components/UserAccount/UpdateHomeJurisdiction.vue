<template>
    <form
        class="home-state-change-section"
        @submit.prevent="handleSubmit"
        aria-labelledby="home-state-change-title"
    >
        <h2 class="section-title" id="home-state-change-title">{{ $t('homeStateChange.formTitle') }}</h2>
        <div class="current-home-state-block">
            <div class="input-label">{{ $t('homeStateChange.currentHomeStateLabel') }}</div>
            <div class="static-value">{{ homeJurisdictionName }}</div>
        </div>
        <InputSelect :formInput="formData.newHomeState" />
        <div class="input-label-subtext">{{ $t('homeStateChange.inputSubtext') }}</div>
        <InputSubmit
            :formInput="formData.submit"
            class="update-home-state-btn"
            :label="$t('homeStateChange.updateButton')"
            :isEnabled="!isFormLoading"
        />
        <Modal v-if="isHomeStateModalVisible" :title="isHomeStateSuccess
            ? $t('homeStateChange.successTitle')
            : isHomeStateError
            ? $t('common.somethingWentWrong')
            : $t('homeStateChange.modalTitle',
                { newState: $tm('common.states')
                    .find((s) => s.abbrev.toLowerCase() === formData.newHomeState.value)?.full
                    || formData.newHomeState.value
                })"
            :isErrorModal="isHomeStateError"
            :showActions="true"
            @close-modal="closeHomeStateModal"
        >
            <template v-slot:content>
                <div v-if="!isHomeStateSuccess && !isHomeStateError">
                    <div class="modal-subtext">{{ $t('homeStateChange.modalSubtext') }}</div>
                </div>
                <div v-else-if="isHomeStateSuccess">
                    <div class="modal-subtext">{{ $t('homeStateChange.successSubtext') }}</div>
                </div>
                <div v-else-if="isHomeStateError">
                <div class="modal-subtext">{{ homeStateErrorMessage }}</div>
                </div>
            </template>
            <template v-slot:actions>
                <div v-if="!isHomeStateSuccess && !isHomeStateError" class="action-button-row">
                    <InputButton
                        :label="$t('common.cancel')"
                        class="cancel-btn"
                        @click="closeHomeStateModal"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="$t('homeStateChange.modalConfirm')"
                        :isEnabled="!isFormLoading"
                        class="submit-btn"
                        @click="submitHomeStateChange"
                    />
                </div>
                <div v-else class="action-button-row">
                    <InputButton
                        :label="$t('common.close')"
                        class="close-btn"
                        @click="closeHomeStateModal"
                    />
                </div>
            </template>
        </Modal>
    </form>
</template>

<script lang="ts" src="./UpdateHomeJurisdiction.ts"></script>
<style scoped lang="less" src="./UserAccount.less"></style>
