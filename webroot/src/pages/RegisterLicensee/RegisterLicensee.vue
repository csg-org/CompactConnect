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
        <template v-if="!isFinalError && !isFormSuccessful && !isConfirmationScreen">
            <h1 class="register-licensee-title">
                {{ $t('account.requestAnAccount') }}
            </h1>
            <div
                class="register-licensee-subtext"
                v-if="!isFinalError && !isFormSuccessful"
                v-html="$t('account.requestAccountSubtext')"
            />
        </template>
        <Card class="register-licensee-card">
            <Transition name="fade" :mode="elementTransitionMode">
                <template v-if="isFinalError">
                    <div class="register-licensee-error-container">
                        <div class="register-licensee-icon-container">
                            <img src="@assets/icons/ico-alert.png" class="icon" :alt="$t('common.error')" />
                        </div>
                        <div class="register-licensee-error-title">{{ $t('account.requestErrorTitle') }}</div>
                        <div class="register-licensee-error-subtext">{{ submitErrorMessage }}</div>
                    </div>
                </template>
                <template v-else-if="!isFormSuccessful">
                    <form @submit.prevent="handleSubmit" class="register-licensee-form" id="register-licensee-form">
                        <div v-if="!isConfirmationScreen" class="register-licensee-form-container">
                            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
                            <a
                                v-if="isMockPopulateEnabled"
                                @click="resetForm()"
                                @keyup.enter="resetForm()"
                                class="clear-form"
                            >{{ $t('common.clear') }}</a>
                            <div v-if="isFormError" class="register-licensee-form-error">
                                {{ submitErrorMessage }}
                            </div>
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
                            <div class="input-email-subtext" v-html="$t('account.requestAccountEmailSubtext')" />
                            <label ref="password">
                                {{ $t('common.password') }}
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    tabindex="-1"
                                    autocomplete="off"
                                />
                            </label>
                            <InputButton
                                @click="handleProceedToConfirmation"
                                class="action-button continue-button register-licensee-continue-to-confirmation-button"
                                :label="(isFormLoading)
                                    ? $t('common.loading')
                                    : $t('common.next')"
                                :isTransparent="false"
                                :isEnabled="!isFormLoading"
                            />
                        </div>
                        <div v-else class="register-licensee-summary-container">
                            <h1 class="register-licensee-title summary-title" id="summary-heading">
                                {{ $t('account.accountSummary') }}
                            </h1>
                            <section role="region" aria-labelledby="summary-heading">
                                <div
                                    class="register-licensee-subtext summary-subtext"
                                    v-html="$t('account.accountSummarySubtext')"
                                />
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('common.firstName') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ formData.firstName.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('common.lastName') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ formData.lastName.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('licensing.stateOfHomeLicense') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ selectedState?.name() || formData.licenseState.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('licensing.licenseType') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value license-type-value">
                                        {{ formData.licenseType.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('licensing.ssnLastFour') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ formData.ssnLastFour.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('common.emailAddress') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ formData.email.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row">
                                    <div class="register-licensee-summary-row-label">
                                        {{ $t('common.dateOfBirth') }}
                                    </div>
                                    <div class="register-licensee-summary-row-value">
                                        {{ formattedDob }}
                                    </div>
                                </div>
                                <div class="register-licensee-summary-row-button-container">
                                    <InputButton
                                        @click="handleBackToForm"
                                        class="action-button submit-button continue-button"
                                        :label="$t('common.back')"
                                        :isTransparent="true"
                                        :isEnabled="!isFormLoading"
                                    />
                                    <InputSubmit
                                        :formInput="formData.submit"
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
                <div v-else class="register-licensee-success-container">
                    <div class="register-licensee-icon-container">
                        <CheckCircle />
                    </div>
                    <div class="register-licensee-success-title">{{ $t('account.requestSuccessTitle') }}</div>
                    <div class="register-licensee-success-subtext">{{ $t('account.requestSuccessSubtext') }}</div>
                    <router-link :to="{ name: 'DashboardPublic' }" class="nav-button">
                        {{ $t('navigation.goToDashboard') }}
                    </router-link>
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

<script lang="ts" src="./RegisterLicensee.ts"></script>
<style scoped lang="less" src="./RegisterLicensee.less"></style>
