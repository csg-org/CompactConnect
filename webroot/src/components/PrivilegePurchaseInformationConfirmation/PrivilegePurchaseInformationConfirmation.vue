<!--
    PrivilegePurchaseInformationConfirmation.vue
    CompactConnect

    Created by InspiringApps on 1/28/2025.
-->

<template>
    <div class="privileges-info-container">
        <form class="confirm-info-form" @submit.prevent="handleSubmit">
            <div  class="confirm-info-core-container">
                <div class="title-row">
                    <h1 class="privilege-purchase-title">
                        {{$t('licensing.privilegePurchaseTitle')}}
                    </h1>
                    <SelectedLicenseInfo class="license-info" />
                </div>
                <div v-if="!areFormInputsSet" class="loading-container">
                    <LoadingSpinner v-if="!userStore.isLoadingAccount" />
                </div>
                <div v-else class="confirm-info-content-container" :class="{ 'right-gap': areFormInputsSet }">
                    <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                    <div class="personal-info-title">
                        {{$t('licensing.personalInfoTitle')}}
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('common.name')}}</div>
                        <div class="chunk-text">{{userFullName}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.homeState')}}</div>
                        <div class="chunk-text">{{homeStateText}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.licenseNumber')}}</div>
                        <div class="chunk-text">{{licenseNumber}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.licenseExpirationDate')}}</div>
                        <div class="chunk-text">{{licenseExpirationDate}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('payment.streetAddress')}}</div>
                        <div class="chunk-text">{{licenseSelectedMailingAddress.street1}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('payment.streetAddress2')}}</div>
                        <div class="chunk-text">{{licenseSelectedMailingAddress.street2}}</div>
                    </div>
                    <div class="chunk-row">
                        <div class="chunk in-row">
                            <div class="chunk-title">{{$t('common.city')}}</div>
                            <div class="chunk-text">{{licenseSelectedMailingAddress.city}}</div>
                        </div>
                        <div class="chunk in-row">
                            <div class="chunk-title">{{$t('common.state')}}</div>
                            <div class="chunk-text">{{mailingAddessStateDisplay}}</div>
                        </div>
                        <div class="chunk in-row">
                            <div class="chunk-title">{{$t('common.zipCode')}}</div>
                            <div class="chunk-text">{{licenseSelectedMailingAddress.zip}}</div>
                        </div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.stateProvidedEmail')}}</div>
                        <div class="chunk-text">{{stateProvidedEmail}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.accountEmail')}}</div>
                        <div class="chunk-text">{{accountEmail}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('common.phoneNumber')}}</div>
                        <div class="chunk-text">{{phoneNumber}}</div>
                    </div>
                    <div class="chunk">
                        <div class="chunk-title">{{$t('licensing.attestations')}}</div>
                        <div class="chunk-text">
                            <InputCheckbox :formInput="formData.homeState" />
                            <InputCheckbox :formInput="formData.address" />
                        </div>
                    </div>
                    <div class="disclaimer-section">
                        {{$t('licensing.incorrectInfoDisclaimer')}}
                    </div>
                </div>
            </div>
            <div v-if="areFormInputsSet" class="button-row">
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
                        :isEnabled="!isFormLoading"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseInformationConfirmation.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseInformationConfirmation.less"></style>
