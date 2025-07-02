<!--
    UpdateHomeJurisdiction.vue
    CompactConnect

    Created by InspiringApps on 7/1/2025.
-->

<template>
    <form
        class="home-jurisdiction-change-section"
        @submit.prevent="handleSubmit"
        aria-labelledby="home-jurisdiction-change-title"
    >
        <h2 class="section-title" id="home-jurisdiction-change-title">{{ $t('homeJurisdictionChange.formTitle') }}</h2>
        <p class="section-subtext">{{ $t('homeJurisdictionChange.formSubtext') }}</p>
        <div class="current-home-jurisdiction-container">
            <div class="input-label">{{ $t('homeJurisdictionChange.currentHomeJurisdictionLabel') }}</div>
            <div class="current-home-jurisdiction">{{ homeJurisdictionName }}</div>
        </div>
        <InputSelect :formInput="formData.newHomeJurisdiction" class="home-jurisdiction-select" />
        <div class="input-label-subtext">{{ $t('homeJurisdictionChange.inputSubtext') }}</div>
        <InputSubmit
            :formInput="formData.submit"
            class="update-home-jurisdiction-btn"
            :label="$t('homeJurisdictionChange.updateButton')"
            :isEnabled="!isFormLoading"
        />
        <Modal
            v-if="isModalVisible"
            class="home-jurisdiction-modal"
            :class="{ 'is-success': isSuccess }"
            :title="!isSuccess
                ? (isError
                    ? $t('common.somethingWentWrong')
                    : $t('homeJurisdictionChange.modalTitle',
                        { newState: $tm('common.states')
                            .find((s) => s.abbrev.toLowerCase() === formData.newHomeJurisdiction.value)?.full
                            || formData.newHomeJurisdiction.value
                        })
                  )
                : ' '"
            :isErrorModal="isError"
            :showActions="true"
            @keyup.esc="closeModal"
        >
            <template v-slot:content>
                <template v-if="!isSuccess && !isError">
                    <div class="modal-subtext">{{ $t('homeJurisdictionChange.modalSubtext') }}</div>
                </template>
                <template v-else-if="isSuccess">
                    <div class="icon-container"><CheckCircleIcon /></div>
                    <h1 class="modal-title">{{ $t('homeJurisdictionChange.successTitle') }}</h1>
                    <div class="modal-subtext">{{ $t('homeJurisdictionChange.successSubtext') }}</div>
                </template>
                <template v-else-if="isError">
                    <div class="modal-subtext">{{ errorMessage }}</div>
                </template>
            </template>
            <template v-slot:actions>
                <div v-if="!isSuccess && !isError" class="action-button-row initial-action-buttons">
                    <InputButton
                        :label="$t('common.cancel')"
                        class="cancel-btn"
                        @click="closeModal"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="$t('homeJurisdictionChange.modalConfirm')"
                        :isEnabled="!isFormLoading"
                        class="submit-btn"
                        @click="submitHomeJurisdictionChange"
                    />
                </div>
                <div v-else class="action-button-row">
                    <InputButton
                        :label="$t('common.close')"
                        class="close-btn"
                        @click="closeModal"
                    />
                </div>
            </template>
        </Modal>
    </form>
</template>

<script lang="ts" src="./UpdateHomeJurisdiction.ts"></script>
<style scoped lang="less" src="./UpdateHomeJurisdiction.less"></style>
