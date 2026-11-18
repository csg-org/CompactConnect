<!--
    ApplicationStart.vue
    CompactConnect

    Created by InspiringApps on 11/17/2026.
-->

<template>
    <div class="application-start-container">
        <div class="application-start-intro">
            <h1 class="application-start-title">{{ $t('application.applyTitle') }}</h1>
            <p class="intro-text">
                {{ $t('application.applyIntro') }}
                <a
                    href="https://psypact.gov"
                    class="text-link"
                    target="_blank"
                    rel="noopener noreferrer"
                >psypact.gov</a>.
            </p>
            <p class="intro-subtext">
                {{ $t('application.applyReviewInfo') }}
                <a
                    href="mailto:info@psypact.gov"
                    class="text-link"
                    target="_blank"
                    rel="noopener noreferrer"
                >info@psypact.gov</a>.
            </p>
        </div>
        <form class="application-start-form" @submit.prevent="handleSubmit">
            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" class="application-start-mock" />
            <section class="application-start-card" aria-labelledby="applying-for-heading">
                <h2 id="applying-for-heading" class="card-title">{{ $t('application.applyingForTitle') }}</h2>
                <div class="type-option">
                    <InputCheckbox :formInput="formData.apit" @change="validateTypeSelection" />
                    <div class="type-description">{{ getTypeDescription(applicationType.APIT) }}</div>
                </div>
                <div class="type-option">
                    <InputCheckbox :formInput="formData.tap" @change="validateTypeSelection" />
                    <div class="type-description">{{ getTypeDescription(applicationType.TAP) }}</div>
                </div>
                <span
                    v-if="formData.tap.errorMessage"
                    :id="`${formData.tap.id}-error`"
                    class="type-error"
                    role="alert"
                    aria-live="assertive"
                >
                    {{ formData.tap.errorMessage }}
                </span>
            </section>
            <section class="application-start-card" aria-labelledby="you-will-need-heading">
                <h2 id="you-will-need-heading" class="card-title">{{ $t('application.youWillNeedTitle') }}</h2>
                <ul class="requirement-list">
                    <li class="requirement-item license">
                        <RibbonIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div class="requirement-title">{{ $t('application.requirementLicense') }}</div>
                            <div class="eligibility-box">
                                <InputSelect :formInput="formData.licenseState" class="license-state-select" />
                            </div>
                        </div>
                    </li>
                    <li class="requirement-item degree">
                        <GraduationCapIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div class="requirement-title">{{ $t('application.requirementDegree') }}</div>
                        </div>
                    </li>
                    <li v-if="isApitSelected" class="requirement-item epassport">
                        <ShieldCheckIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div class="requirement-title">
                                {{ $t('application.requirementEPassport') }}
                                <a
                                    :href="ePassportUrl"
                                    class="text-link external-link"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    {{ $t('application.getEPassport') }}
                                    <ExternalLinkIcon class="external-link-icon" aria-hidden="true" />
                                    <span class="visually-hidden">{{ $t('common.opensInNewTab') }}</span>
                                </a>
                            </div>
                            <div class="requirement-subtext">{{ $t('application.requirementEPassportSubtext') }}</div>
                        </div>
                    </li>
                    <li v-if="isTapSelected" class="requirement-item ipc">
                        <ShieldCheckIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div class="requirement-title">
                                {{ $t('application.requirementIpc') }}
                                <a
                                    :href="ipcUrl"
                                    class="text-link external-link"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    {{ $t('application.getIpc') }}
                                    <ExternalLinkIcon class="external-link-icon" aria-hidden="true" />
                                    <span class="visually-hidden">{{ $t('common.opensInNewTab') }}</span>
                                </a>
                            </div>
                            <div class="requirement-subtext">{{ $t('application.requirementIpcSubtext') }}</div>
                        </div>
                    </li>
                    <li class="requirement-item fee">
                        <CreditCardIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div v-if="isFeeUnavailable" class="requirement-title fee-unavailable" role="alert">
                                {{ $t('application.requirementFeeUnavailable') }}
                            </div>
                            <div v-else class="requirement-title">
                                {{ $t('application.requirementFee', { fee: totalFeeDisplay }) }}
                            </div>
                        </div>
                    </li>
                    <li class="requirement-item time">
                        <ClockIcon class="requirement-icon" />
                        <div class="requirement-content">
                            <div class="requirement-title">{{ $t('application.requirementTime') }}</div>
                        </div>
                    </li>
                </ul>
            </section>
            <InputSubmit
                :formInput="formData.submit"
                :label="submitLabel"
                :isEnabled="!isFormLoading && !isFeeUnavailable"
                :isTransparent="false"
                class="start-application-submit"
            />
        </form>
    </div>
</template>

<script lang="ts" src="./ApplicationStart.ts"></script>
<style scoped lang="less" src="./ApplicationStart.less"></style>
