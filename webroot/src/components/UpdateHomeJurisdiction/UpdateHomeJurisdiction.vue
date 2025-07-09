<!--
    UpdateHomeJurisdiction.vue
    CompactConnect

    Created by InspiringApps on 7/1/2025.
-->

<template>
    <div class="home-jurisdiction-change-section">
        <form
            @submit.prevent="handleSubmit"
            aria-labelledby="home-jurisdiction-change-title"
        >
            <h2 class="section-title" id="home-jurisdiction-change-title">
                {{ $t('homeJurisdictionChange.formTitle') }}
            </h2>
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
        </form>
        <Modal
            v-if="isConfirmJurisdictionModalOpen"
            id="home-jurisdiction-modal"
            class="home-jurisdiction-modal"
            :class="{ 'is-success': isSuccess }"
            :title="jurisdictionModalTitle"
            :isErrorModal="isError"
            :showActions="true"
            @close-modal="closeConfirmJurisdictionModal"
            @keydown.tab="focusTrapJurisdiction($event)"
            @keyup.esc="closeConfirmJurisdictionModal"
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
                        id="jurisdiction-cancel-btn"
                        class="cancel-btn"
                        :label="$t('common.cancel')"
                        :isTransparent="true"
                        :onClick="closeConfirmJurisdictionModal"
                    />
                    <InputSubmit
                        class="submit-btn"
                        :formInput="formData.confirm"
                        :label="$t('homeJurisdictionChange.modalConfirm')"
                        :isEnabled="!isFormLoading"
                        @click="submitHomeJurisdictionChange"
                    />
                </div>
                <div v-else class="action-button-row">
                    <InputSubmit
                        class="close-btn"
                        :formInput="formData.close"
                        :label="$t('common.close')"
                        :isEnabled="!isFormLoading && isSuccess"
                        @click="closeConfirmJurisdictionModal"
                    />
                </div>
            </template>
        </Modal>
    </div>
</template>

<script lang="ts" src="./UpdateHomeJurisdiction.ts"></script>
<style scoped lang="less" src="./UpdateHomeJurisdiction.less"></style>
