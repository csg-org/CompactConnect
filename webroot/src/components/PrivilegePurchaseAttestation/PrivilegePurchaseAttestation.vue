<!--
    PrivilegePurchaseAttestation.vue
    CompactConnect

    Created by InspiringApps on 11/4/2024.
-->

<template>
    <div class="privilege-purchase-attestation-container">
        <form class="privilege-purchase-attestation-form" @submit.prevent="handleSubmit">
            <div class="privilege-purchase-attestation-form-container">
                <ProgressBar :progressPercent="progressPercent" />
                <h1 class="form-title">{{ $t('licensing.attestations') }}</h1>
                <div v-if="!areFormInputsSet" class="loading-container">
                    <LoadingSpinner v-if="!userStore.isLoadingAccount" />
                </div>
                <div v-else>
                    <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                    <InputRadioGroup :formInput="formData.investigations" />
                    <div class="form-section-title">{{ $t('licensing.discipline') }} *</div>
                    <InputCheckbox :formInput="formData.disciplineCurrent" />
                    <InputCheckbox :formInput="formData.disciplinePrior" />
                    <div class="form-section-title form-section-gap">
                        {{ $t('licensing.provisionOfInformation') }} *
                    </div>
                    <InputCheckbox :formInput="formData.trueInformation" />
                    <div class="form-section-title form-section-gap">
                        {{ $t('licensing.militaryAffiliation') }} *
                    </div>
                    <InputCheckbox :formInput="formData.militaryAffiliation" />
                </div>
            </div>
            <div v-if="areFormInputsSet" class="button-row">
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
