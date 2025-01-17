<!--
    RegisterLicensee.vue
    CompactConnect

    Created by InspiringApps on 1/14/2025.
-->

<template>
    <Section class="register-licensee-section-container">
        <div class="register-licensee-logo-container">
            <img
                src="@assets/logos/compact-connect-logo.png"
                class="register-licensee-logo"
                :alt="$t('common.appName')"
            />
        </div>
        <h1 v-if="!isFinalError && !isFormSuccessful" class="register-licensee-title">
            {{ $t('account.requestAnAccount') }}
        </h1>
        <Card class="register-licensee-card">
            <Transition name="fade" :mode="elementTransitionMode">
                <div v-if="isFinalError" class="register-licensee-error-container">
                    <div class="register-licensee-icon-container">
                        <img src="@assets/icons/ico-alert.png" class="icon" :alt="$t('common.error')" />
                    </div>
                    <div class="register-licensee-error-title">{{ $t('account.requestErrorTitle') }}</div>
                    <div class="register-licensee-error-subtext">{{ submitErrorMessage }}</div>
                </div>
                <div v-else-if="!isFormSuccessful" class="register-licensee-form-container">
                    <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                    <a
                        v-if="isMockPopulateEnabled"
                        @click="resetForm()"
                        @keyup.enter="resetForm()"
                        class="clear-form"
                    >{{ $t('common.clear') }}</a>
                    <form @submit.prevent="handleSubmit" class="register-licensee-form">
                        <InputText :formInput="formData.firstName" />
                        <InputText :formInput="formData.lastName" />
                        <InputText :formInput="formData.email" />
                        <InputText :formInput="formData.ssnLastFour" @input="formatSsn()" />
                        <InputDate :formInput="formData.dob" />
                        <InputSelect :formInput="formData.licenseState" />
                        <InputSelect :formInput="formData.licenseType" @input="setCompactFromLicenseType()" />
                        <label ref="password">
                            {{ $t('common.password') }}
                            <input type="password" id="password" name="password" tabindex="-1" autocomplete="off" />
                        </label>
                        <InputSubmit
                            :formInput="formData.submit"
                            :label="submitLabel"
                            class="input-submit"
                            :isEnabled="!isFormLoading"
                        />
                    </form>
                </div>
                <div v-else class="register-licensee-success-container">
                    <div class="register-licensee-icon-container">
                        <CheckCircle />
                    </div>
                    <div class="register-licensee-success-title">{{ $t('account.requestSuccessTitle') }}</div>
                    <div class="register-licensee-success-subtext">{{ $t('account.requestSuccessSubtext') }}</div>
                </div>
            </Transition>
        </Card>
        <div ref="recaptcha"></div>
    </Section>
</template>

<script lang="ts" src="./RegisterLicensee.ts"></script>
<style scoped lang="less" src="./RegisterLicensee.less"></style>
