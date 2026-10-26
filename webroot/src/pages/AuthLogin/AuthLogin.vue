<!--
    AuthLogin.vue
    CompactConnect

    Created by InspiringApps on 10/22/2026.
-->

<template>
    <Section class="auth-login-container">
        <Card v-if="!isSupportedTarget" class="auth-card">
            <div class="auth-logo-container">
                <img
                    v-if="$isAppModePsyPact"
                    src="@assets/logos/psypact-logo.png"
                    class="auth-logo"
                    :alt="$t('common.appNamePsyPact')"
                />
                <img
                    v-else
                    src="@assets/logos/compact-connect-logo.png"
                    class="auth-logo"
                    :alt="$t('common.appName')"
                />
            </div>
            <h1 class="auth-title">{{ $t('auth.unsupportedLogin') }}</h1>
            <router-link class="auth-text-link" :to="{ name: 'DashboardPublic' }">
                {{ $t('auth.backToDashboard') }}
            </router-link>
        </Card>
        <Card v-else class="auth-card">
            <div class="auth-logo-container">
                <img
                    v-if="$isAppModePsyPact"
                    src="@assets/logos/psypact-logo.png"
                    class="auth-logo"
                    :alt="$t('common.appNamePsyPact')"
                />
                <img
                    v-else
                    src="@assets/logos/compact-connect-logo.png"
                    class="auth-logo"
                    :alt="$t('common.appName')"
                />
            </div>
            <h1 ref="stepTitle" class="auth-title" tabindex="-1">{{ title }}</h1>
            <p v-if="instructions" class="auth-instructions">{{ instructions }}</p>
            <p v-if="isMfaSetupStep" class="auth-countdown">{{ countdownLabel }}</p>
            <form @submit.prevent="handleSubmit">
                <InputText v-if="showsEmail" :formInput="formData.email" />
                <InputPassword
                    v-if="showsLoginPassword"
                    :formInput="formData.password"
                    :joiMessages="joiMessages"
                    :showEyeIcon="true"
                    :showRequirements="false"
                />
                <div v-if="isMfaSetupStep" class="mfa-setup">
                    <img
                        v-if="qrCodeDataUrl"
                        class="mfa-qr"
                        :src="qrCodeDataUrl"
                        :alt="$t('auth.mfaSetupQr')"
                    />
                    <label class="setup-key-label" for="mfa-setup-key">{{ $t('auth.mfaSetupKey') }}</label>
                    <input
                        id="mfa-setup-key"
                        class="setup-key"
                        type="text"
                        readonly
                        :value="totpSecret"
                    />
                    <InputButton
                        id="copy-setup-key"
                        :label="copyLabel"
                        :onClick="copySetupKey"
                        :shouldTransformText="false"
                    />
                    <div class="copy-status" aria-live="polite" role="status">{{ copyStatus }}</div>
                </div>
                <InputText v-if="isForgotPasswordConfirmStep" :formInput="formData.resetCode" />
                <InputPassword
                    v-if="showsNewPassword"
                    :formInput="formData.newPassword"
                    :joiMessages="joiMessages"
                    :showEyeIcon="true"
                    @input="validatePasswordMatch"
                />
                <InputPassword
                    v-if="showsNewPassword"
                    :formInput="formData.confirmPassword"
                    :joiMessages="joiMessages"
                    :showEyeIcon="true"
                    :showRequirements="false"
                    @input="validatePasswordMatch"
                    @blur="validatePasswordMatch"
                />
                <InputText v-if="showsMfaCode" :formInput="formData.mfaCode" />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="isSubmitEnabled"
                />
            </form>
            <button
                v-if="isLoginStep"
                type="button"
                class="auth-text-link text-like"
                @click="showForgotPassword"
            >
                {{ $t('auth.forgotPassword') }}
            </button>
            <button
                v-else
                type="button"
                class="auth-text-link text-like"
                @click="showLogin"
            >
                {{ $t('auth.backToLogin') }}
            </button>
        </Card>
    </Section>
</template>

<script lang="ts" src="./AuthLogin.ts"></script>
<style scoped lang="less" src="./AuthLogin.less"></style>
