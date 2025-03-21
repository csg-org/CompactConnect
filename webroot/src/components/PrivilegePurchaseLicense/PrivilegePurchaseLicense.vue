<!--
    PrivilegePurchaseLicense.vue
    CompactConnect

    Created by InspiringApps on 3/3/2025.
-->

<template>
    <div class="select-license-container">
        <form class="license-form" @submit.prevent="handleSubmit">
            <div class="select-license-core-container">
                <h1 class="privilege-purchase-title">
                    {{$t('licensing.privilegePurchaseTitle')}}
                </h1>
                <div class="select-license-title">
                    {{$t('licensing.selectLicense')}}
                </div>
                <LoadingSpinner v-if="isLoading"></LoadingSpinner>
                <div v-else>
                    <div class="select-container">
                        <InputSelect :formInput="formData.licenseSelect" class="license-select" />
                    </div>
                </div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    :aria-label="cancelText"
                    class="icon icon-close-modal"
                    @click="handleCancelClicked"
                />
                <div class="right-cell">
                    <InputButton
                        :label="backText"
                        :aria-label="backText"
                        class="back-button"
                        :isTransparent="true"
                        @click="handleBackClicked"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseLicense.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseLicense.less"></style>
