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
                <div class="form-nav-buttons">
                    <InputSubmit
                        :formInput="formData.submit"
                        class="form-nav-button"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading"
                    />
                    <InputButton
                        :label="backText"
                        :aria-label="backText"
                        class="form-nav-button back-button"
                        :isTransparent="true"
                        @click="handleBackClicked"
                    />
                </div>
                <div class="form-override-buttons">
                    <InputButton
                        :label="cancelText"
                        :isTextLike="true"
                        :aria-label="cancelText"
                        class="form-override-button icon icon-close-modal"
                        @click="handleCancelClicked"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseLicense.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseLicense.less"></style>
