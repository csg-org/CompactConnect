<!--
    StateUpload.vue
    CompactConnect

    Created by InspiringApps on 6/18/2024.
-->

<template>
    <div class="state-upload-container">
        <h1>{{ $t('stateUpload.formTitle') }}</h1>
        <div class="sub-title">{{ $t('stateUpload.formSubtext') }}</div>
        <Card class="state-upload">
            <Transition name="fade" :mode="elementTransitionMode">
                <LoadingSpinner v-if="isInitializing" />
                <div v-else-if="!isFormSuccessful" class="state-upload-form">
                    <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                    <div class="state-upload-form-container">
                        <form @submit.prevent="handleSubmit">
                            <InputSelect :formInput="formData.state" class="state-select" />
                            <InputFile :formInput="formData.files" class="file-select" />
                            <InputSubmit
                                :formInput="formData.submit"
                                :label="submitLabel"
                                :isEnabled="!isFormLoading"
                            />
                        </form>
                    </div>
                </div>
                <div v-else class="state-upload-success">
                    <div class="icon-container">
                        <CheckCircle />
                    </div>
                    <h1 class="success-title">{{ $t('stateUpload.successTitle') }}</h1>
                    <div class="success-subtitle">{{ $t('stateUpload.successSubTitle') }}</div>
                    <div class="success-actions">
                        <button class="success-btn transparent" @click="resetForm">Upload another</button>
                        <button class="success-btn" @click="resetForm">Done</button>
                    </div>
                </div>
            </Transition>
        </Card>
    </div>
</template>

<script lang="ts" src="./StateUpload.ts"></script>
<style scoped lang="less" src="./StateUpload.less"></style>
