<!--
    PrivilegePurchaseInformationConfirmation.vue
    CompactConnect

    Created by InspiringApps on 1/28/2025.
-->

<template>
    <div class="privileges-info-container">
        <form class="confirm-info-form" @submit.prevent="handleSubmit">
            <div class="confirm-info-core-container">
                <div class="privilege-purchase-title">
                    {{$t('licensing.privilegePurchaseTitle')}}
                </div>
                <div class="personal-info-title">
                    {{$t('licensing.personalInfoTitle')}}
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
                        :label="$t('common.confirm')"
                        :isEnabled="!isFormLoading && areAllAttestationsChecked"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseInformationConfirmation.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseInformationConfirmation.less"></style>
