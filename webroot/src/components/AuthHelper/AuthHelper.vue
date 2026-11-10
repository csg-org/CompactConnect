<!--
    AuthHelper.vue
    CompactConnect

    Created by InspiringApps on 10/28/2026.
-->

<template>
    <aside v-if="isMfaSetup" class="auth-helper">
        <h2>{{ $t('auth.helper.mfaSetupTitle') }}</h2>
        <p>{{ $t('auth.helper.mfaSetupIntro') }}</p>
        <h3>{{ $t('auth.helper.mfaAppsTitle') }}</h3>
        <ul>
            <li>
                {{ $t('auth.helper.googleAuthenticator') }}
                <span class="app-links">
                    <a
                        href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.android') }}</a>
                    <span class="app-link-separator" aria-hidden="true">|</span>
                    <a
                        href="https://apps.apple.com/app/google-authenticator/id388497605"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.ios') }}</a>
                </span>
            </li>
            <li>
                {{ $t('auth.helper.microsoftAuthenticator') }}
                <span class="app-links">
                    <a
                        href="https://play.google.com/store/apps/details?id=com.azure.authenticator"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.android') }}</a>
                    <span class="app-link-separator" aria-hidden="true">|</span>
                    <a
                        href="https://apps.apple.com/app/microsoft-authenticator/id983156458"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.ios') }}</a>
                </span>
            </li>
            <li>
                {{ $t('auth.helper.authy') }}
                <span class="app-links">
                    <a
                        href="https://play.google.com/store/apps/details?id=com.authy.authy"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.android') }}</a>
                    <span class="app-link-separator" aria-hidden="true">|</span>
                    <a
                        href="https://apps.apple.com/app/twilio-authy/id494168017"
                        target="_blank"
                        rel="noopener noreferrer"
                    >{{ $t('auth.helper.ios') }}</a>
                </span>
            </li>
        </ul>
        <h3>{{ $t('auth.helper.mfaStepsTitle') }}</h3>
        <ol>
            <li>{{ $t('auth.helper.mfaStepDownload') }}</li>
            <li>{{ $t('auth.helper.mfaStepScan') }}</li>
            <li>{{ $t('auth.helper.mfaStepCode') }}</li>
            <li>{{ $t('auth.helper.mfaStepContinue') }}</li>
        </ol>
        <p>{{ $t('auth.helper.mfaTimeLimit') }}</p>
    </aside>
    <p v-else-if="instructions" class="auth-instructions">{{ instructions }}</p>
</template>

<script lang="ts" src="./AuthHelper.ts"></script>
<style scoped lang="less" src="./AuthHelper.less"></style>
