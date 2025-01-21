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
                    :isTextLike="true"
                    :label="$t('common.cancel')"
                    :aria-label="$t('common.cancel')"
                    class="cancel"
                    @click="handleCancelClicked"
                />
                <div class="right-cell">
                    <InputButton
                        :label="$t('common.back')"
                        :aria-label="$t('common.back')"
                        class="back"
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

<script lang="ts" src="./PrivilegePurchaseAttestation.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseAttestation.less"></style>
