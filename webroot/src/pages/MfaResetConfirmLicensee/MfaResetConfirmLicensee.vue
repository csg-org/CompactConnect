<!--
    MfaResetConfirmLicensee.vue
    CompactConnect

    Created by InspiringApps on 8/22/2025.
-->

<template>
    <Section class="mfa-reset-confirmation-container">
        <div v-if="isLoading" class="loading-container">
            <div class="loading-title">{{ $t('account.resetAccountVerifying') }}</div>
            <LoadingSpinner :noBgColor="true" />
        </div>
        <Card v-else-if="isSuccess" class="status-card success">
            <div class="icon-container"><CheckCircle /></div>
            <div class="status-title">{{ $t('account.resetAccountSuccessTitle') }}</div>
            <div class="status-description">{{ $t('account.resetAccountSuccessSubtext1') }}</div>
            <div class="status-description">{{ $t('account.resetAccountSuccessSubtext2') }}</div>
            <div class="actions">
                <InputButton
                    @click="goToLogin"
                    class="action-button success login"
                    :label="$t('account.resetAccountActionLogin')"
                />
            </div>
        </Card>
        <Card v-else class="status-card error">
            <div class="icon-container"><AlertTriangle /></div>
            <div class="status-title">{{ $t('account.resetAccountErrorTitle') }}</div>
            <div class="status-description">{{ $t('account.resetAccountErrorSubtext') }}</div>
            <div v-if="serverMessage" class="server-message">{{ serverMessage }}</div>
            <div class="actions">
                <InputButton
                    @click="goToLogin"
                    class="action-button login"
                    :label="$t('account.resetAccountActionLogin')"
                />
                <InputButton
                    @click="goToDashboard"
                    class="action-button dashboard"
                    :label="$t('account.resetAccountActionDashboard')"
                />
            </div>
        </Card>
        <div ref="recaptcha"></div>
    </Section>
</template>

<script lang="ts" src="./MfaResetConfirmLicensee.ts"></script>
<style scoped lang="less" src="./MfaResetConfirmLicensee.less"></style>
