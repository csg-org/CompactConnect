<!--
    PrivacyPolicy.vue
    CompactConnect

    Created by InspiringApps on 7/30/2025.
-->

<template>
    <div class="privacy-policy-container">
        <div class="privacy-policy-content-container">
            <InputButton
                :label="$t('common.back')"
                :aria-label="$t('common.back')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="back-btn"
                @click="goBack"
            />
            <h1 class="privacy-policy-title">{{ $t('privacyPolicy.title') }}</h1>
            <p>{{ $t('privacyPolicy.introSubtext') }}</p>
            <h2>{{ $t('privacyPolicy.whatDataIsCollectedTitle') }}</h2>
            <ul>
                <li>{{ $t('privacyPolicy.collectedDataEmail') }}</li>
                <li>{{ $t('privacyPolicy.collectedDataDevice') }}</li>
            </ul>
            <h2>{{ $t('privacyPolicy.whatIsDoneWithThisInfoTitle') }}</h2>
            <p>{{ $t('privacyPolicy.whatIsDoneWithThisInfoSubtext') }}</p>
            <h2>{{ $t('privacyPolicy.howIsMyDataProtectedTitle') }}</h2>
            <p>{{ $t('privacyPolicy.howIsMyDataProtectedSubtext') }}</p>
            <h2>{{ $t('privacyPolicy.changesToThisPolicyTitle') }}</h2>
            <p>{{ $t('privacyPolicy.changesToThisPolicySubtext') }}</p>
            <h2>{{ $t('privacyPolicy.disclaimerTitle') }}</h2>
            <p>{{ $t('privacyPolicy.disclaimerSubtext') }}</p>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivacyPolicy.ts"></script>
<style scoped lang="less" src="./PrivacyPolicy.less"></style>
