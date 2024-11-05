<!--
    PrivilegePurchaseAttestation.vue
    CompactConnect

    Created by InspiringApps on 11/4/2024.
-->

<template>
    <div class="privilege-purchase-attestation-container">
        <form class="privilege-form" @submit.prevent="handleSubmit">
            <div class="attestation-text">
                Attestations
            </div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="handleCancelClicked"
                />
                <div class="right-cell">
                    <InputButton
                        :label="backText"
                        aria-label="close modal"
                        class="back-button"
                        @click="handleBackClicked"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen && areAllJurisprudenceConfirmed"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseAttestation.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseAttestation.less"></style>
