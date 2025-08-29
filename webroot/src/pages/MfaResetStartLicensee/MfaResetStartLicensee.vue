<!--
    MfaResetStartLicensee.vue
    CompactConnect

    Created by InspiringApps on 8/22/2025.
-->

<template>
    <Section class="mfa-reset-licensee-section-container">
        <div class="mfa-reset-licensee-logo-container">
            <img
                src="@assets/logos/compact-connect-logo.png"
                class="mfa-reset-licensee-logo"
                :alt="$t('common.appName')"
            />
        </div>
        <template v-if="!isFinalError && !isFormSuccessful && !isConfirmationScreen">
            <h1 class="mfa-reset-licensee-title">
                {{ $t('account.resetAccount') }}
            </h1>
            <div
                class="mfa-reset-licensee-subtext"
                v-if="!isFinalError && !isFormSuccessful"
                v-html="$t('account.resetAccountSubtext1')"
            />
            <div
                class="mfa-reset-licensee-subtext"
                v-if="!isFinalError && !isFormSuccessful"
                v-html="$t('account.resetAccountSubtext2')"
            />
        </template>
        <Card class="mfa-reset-licensee-card">
            <Transition name="fade" :mode="elementTransitionMode">
                <template v-if="isFinalError">
                    <div class="mfa-reset-licensee-error-container">
                        <div class="mfa-reset-licensee-icon-container">
                            <img src="@assets/icons/ico-alert.png" class="icon" :alt="$t('common.error')" />
                        </div>
                        <div class="mfa-reset-licensee-error-title">{{ $t('account.requestErrorTitle') }}</div>
                        <div class="mfa-reset-licensee-error-subtext">{{ submitErrorMessage }}</div>
                    </div>
                </template>
                <template v-else-if="!isFormSuccessful">
                    <form @submit.prevent="handleSubmit" class="mfa-reset-licensee-form" id="mfa-reset-licensee-form">
                        <div v-if="!isConfirmationScreen" class="mfa-reset-licensee-form-container">
                            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" /><br />
                            <a
                                v-if="isMockPopulateEnabled"
                                @click="resetForm()"
                                @keyup.enter="resetForm()"
                                class="clear-form"
                            >{{ $t('common.clear') }}</a>
                            <InputText :formInput="formData.firstName" />
                            <InputText :formInput="formData.lastName" />
                            <InputText :formInput="formData.ssnLastFour" @input="formatSsn()" />
                            <InputDate
                                :formInput="formData.dob"
                                :yearRange="[1920, new Date().getFullYear()]"
                                :maxDate="new Date()"
                                :preventMinMaxNavigation="true"
                                :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                                :startDate="new Date(1975, 0, 1)"
                            />
                            <InputSelect :formInput="formData.licenseState" />
                            <InputSelect :formInput="formData.licenseType" />
                            <InputText :formInput="formData.email" class="input-email-component" />
                            <div class="input-email-subtext" v-html="$t('account.resetAccountEmailSubtext')" />
                            <InputPassword
                                :formInput="formData.password"
                                :joiMessages="joiMessages"
                                :showEyeIcon="true"
                                :showRequirements="false"
                                class="input-password-component"
                            />
                            <div class="input-password-subtext" v-html="$t('account.resetAccountPasswordSubtext')" />
                            <div class="forgot-password-container">
                                <a
                                    :href="hostedForgotPasswordUriLicensee"
                                    class="forgot-password-link"
                                    rel="noopener noreferrer"
                                >
                                    {{ $t('account.resetAccountForgotPassword') }}
                                </a>
                            </div>
                            <label ref="reenterPassword">
                                {{ $t('common.password') }}
                                <input
                                    type="password"
                                    id="reenter-password"
                                    name="reenter-password"
                                    tabindex="-1"
                                    autocomplete="off"
                                />
                            </label>
                            <InputSubmit
                                :formInput="formData.handleSubmitInitial"
                                @click="handleProceedToConfirmation"
                                class="action-button continue-button mfa-reset-licensee-continue-to-confirmation-button"
                                :label="(isFormLoading)
                                    ? $t('common.loading')
                                    : $t('common.next')"
                                :isTransparent="false"
                                :isEnabled="!isFormLoading"
                            />
                        </div>
                        <div v-else class="mfa-reset-licensee-summary-container">
                            <h1 class="mfa-reset-licensee-title summary-title" id="summary-heading">
                                {{ $t('account.resetAccountSummary') }}
                            </h1>
                            <section role="region" aria-labelledby="summary-heading">
                                <div
                                    class="mfa-reset-licensee-subtext summary-subtext"
                                    v-html="$t('account.resetAccountSummarySubtext')"
                                />
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('common.firstName') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ formData.firstName.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('common.lastName') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ formData.lastName.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('licensing.stateOfHomeLicense') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ selectedStateName || formData.licenseState.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('licensing.licenseType') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value license-type-value">
                                        {{ formData.licenseType.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('licensing.ssnLastFour') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ formData.ssnLastFour.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('common.emailAddress') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ formData.email.value }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('common.dateOfBirth') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value">
                                        {{ formattedDob }}
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row">
                                    <div class="mfa-reset-licensee-summary-row-label">
                                        {{ $t('common.password') }}
                                    </div>
                                    <div class="mfa-reset-licensee-summary-row-value placeholder">
                                        Hidden for security
                                    </div>
                                </div>
                                <div class="mfa-reset-licensee-summary-row-button-container">
                                    <InputButton
                                        @click="handleBackToForm"
                                        class="action-button submit-button continue-button"
                                        :label="$t('common.back')"
                                        :isTransparent="true"
                                        :isEnabled="!isFormLoading"
                                    />
                                    <InputSubmit
                                        :formInput="formData.handleSubmitConfirmation"
                                        :label="$t('common.confirm')"
                                        class="input-submit"
                                        :isTransparent="false"
                                        :isEnabled="!isFormLoading"
                                    />
                                </div>
                            </section>
                        </div>
                    </form>
                </template>
                <div v-else class="mfa-reset-licensee-success-container">
                    <div class="mfa-reset-licensee-icon-container">
                        <CheckCircle />
                    </div>
                    <div class="mfa-reset-licensee-success-title">{{ $t('account.requestSuccessTitle') }}</div>
                    <div class="mfa-reset-licensee-success-subtext">{{ $t('account.requestSuccessSubtext') }}</div>
                    <router-link :to="{ name: 'DashboardPublic' }" class="nav-button">
                        {{ $t('navigation.goToDashboard') }}
                    </router-link>
                    <div v-if="isUsingMockApi" class="mock-nav">
                        <router-link class="mock-link" :to="{
                            name: 'DashboardPublic',
                            query: {
                                bypass: 'recovery-practitioner',
                                compact: 'octp',
                                providerId: 'test-provider-id',
                                recoveryId: 'test-recovery-id',
                            },
                        }">
                            Mock go to confirmation URL (Success)
                        </router-link>
                        <router-link class="mock-link" :to="{
                            name: 'DashboardPublic',
                            query: {
                                bypass: 'recovery-practitioner',
                            },
                        }">
                            Mock go to confirmation URL (Error)
                        </router-link>
                    </div>
                </div>
            </Transition>
        </Card>
        <div ref="recaptcha"></div>
        <div class="recaptcha-terms">
            {{ $t('recaptcha.googleDesc') }}
            <a
                href="https://policies.google.com/privacy"
                rel="noopener noreferrer"
                class="recaptcha-link"
            >{{ $t('recaptcha.privacyPolicy') }}</a>
            {{ $t('recaptcha.and') }}
            <a
                href="https://policies.google.com/terms"
                rel="noopener noreferrer"
                class="recaptcha-link"
            >{{ $t('recaptcha.terms') }}</a>
            {{ $t('recaptcha.apply') }}.
        </div>
    </Section>
</template>

<script lang="ts" src="./MfaResetStartLicensee.ts"></script>
<style scoped lang="less" src="./MfaResetStartLicensee.less"></style>
