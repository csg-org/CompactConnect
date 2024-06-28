<!--
    StateUpload.vue
    CompactConnect

    Created by InspiringApps on 6/18/2024.
-->

<template>
    <Card class="state-upload">
        <Transition name="fade">
        <LoadingSpinner v-if="isInitializing" />
        </Transition>
        <Transition name="fade" mode="out-in">
        <div v-if="!isFormSuccessful" class="state-upload-form">
            <h1>{{ $t('stateUpload.formTitle') }}</h1>
            <div class="sub-title">{{ $t('stateUpload.formSubtext') }}</div>
            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
            <div class="state-upload-form-container">
                <form @submit.prevent="handleSubmit">
                    <InputSelect :formInput="formData.compact" class="compact-select" />
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
            <h1>{{ $t('stateUpload.successTitle') }}</h1>
            <div class="sub-title">{{ $t('stateUpload.successSubtext') }}</div>
        </div>
        </Transition>
    </Card>
</template>

<script lang="ts" src="./StateUpload.ts"></script>
<style scoped lang="less" src="./StateUpload.less"></style>
