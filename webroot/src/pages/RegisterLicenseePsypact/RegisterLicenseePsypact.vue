<!--
    RegisterLicenseePsypact.vue
    CompactConnect

    Created by InspiringApps on 11/16/2026.
-->

<template>
    <Section class="register-licensee-psypact-section-container">
        <div class="register-licensee-psypact-logo-container">
            <img
                src="@assets/logos/psypact-logo.png"
                class="register-licensee-psypact-logo"
                :alt="$t('common.appNamePsyPact')"
            />
        </div>
        <Card class="register-licensee-psypact-card" :allowOverflow="true">
            <Transition name="fade" :mode="elementTransitionMode">
                <template v-if="isFinalError">
                    <div class="register-licensee-psypact-error-container">
                        <div class="register-licensee-psypact-icon-container">
                            <img src="@assets/icons/ico-alert.png" class="icon" :alt="$t('common.error')" />
                        </div>
                        <div class="register-licensee-psypact-error-title">{{ $t('account.requestErrorTitle') }}</div>
                        <div class="register-licensee-psypact-error-subtext">{{ submitErrorMessage }}</div>
                    </div>
                </template>
                <template v-else-if="!isFormSuccessful">
                    <form
                        @submit.prevent="handleSubmit"
                        class="register-licensee-psypact-form"
                        id="register-licensee-psypact-form"
                    >
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
                        <div v-if="!isConfirmationScreen" class="register-licensee-psypact-form-container">
                            <h1 class="register-licensee-psypact-title">
                                {{ $t('account.createAnAccount') }}
                            </h1>
                            <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" /><br />
                            <a
                                v-if="isMockPopulateEnabled"
                                @click="resetForm()"
                                @keyup.enter="resetForm()"
                                class="clear-form"
                            >{{ $t('common.clear') }}</a>
                            <InputText :formInput="formData.firstName" />
                            <InputText :formInput="formData.lastName" />
                            <InputText :formInput="formData.email" />
                            <InputPassword
                                :formInput="formData.newPassword"
                                :joiMessages="joiMessages"
                                :showEyeIcon="true"
                                @input="validatePasswordMatch"
                            />
                            <InputPassword
                                :formInput="formData.confirmPassword"
                                :joiMessages="joiMessages"
                                :showEyeIcon="true"
                                :showRequirements="false"
                                @input="validatePasswordMatch"
                                @blur="validatePasswordMatch"
                            />
                            <InputSubmit
                                :formInput="formData.handleSubmitInitial"
                                @click.prevent="handleProceedToConfirmation"
                                class="action-button continue-button register-licensee-psypact-continue-to-confirmation"
                                :label="(isFormLoading)
                                    ? $t('common.loading')
                                    : $t('account.createAccount')"
                                :isTransparent="false"
                                :isEnabled="!isFormLoading"
                            />
                        </div>
                        <div v-else class="register-licensee-psypact-summary-container">
                            <h1 class="register-licensee-psypact-title summary-title" id="summary-heading">
                                {{ $t('account.accountSummary') }}
                            </h1>
                            <section role="region" aria-labelledby="summary-heading">
                                <div class="register-licensee-psypact-summary-row">
                                    <div class="register-licensee-psypact-summary-row-label">
                                        {{ $t('common.firstName') }}
                                    </div>
                                    <div class="register-licensee-psypact-summary-row-value summary-first-name">
                                        {{ formData.firstName.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-psypact-summary-row">
                                    <div class="register-licensee-psypact-summary-row-label">
                                        {{ $t('common.lastName') }}
                                    </div>
                                    <div class="register-licensee-psypact-summary-row-value summary-last-name">
                                        {{ formData.lastName.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-psypact-summary-row">
                                    <div class="register-licensee-psypact-summary-row-label">
                                        {{ $t('common.emailAddress') }}
                                    </div>
                                    <div class="register-licensee-psypact-summary-row-value summary-email">
                                        {{ formData.email.value }}
                                    </div>
                                </div>
                                <div class="register-licensee-psypact-summary-row-button-container">
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
                <div v-else-if="isFormSuccessful" class="register-licensee-psypact-success-container">
                    <div class="register-licensee-psypact-icon-container">
                        <CheckCircle />
                    </div>
                    <div class="register-licensee-psypact-success-title">
                        {{ $t('account.createAccountSuccessTitle') }}
                    </div>
                    <div class="register-licensee-psypact-success-subtext">
                        {{ $t('account.createAccountSuccessSubtext') }}
                    </div>
                    <router-link :to="{ name: 'DashboardPublic' }" class="nav-button">
                        {{ $t('navigation.goToDashboard') }}
                    </router-link>
                </div>
            </Transition>
        </Card>
        <div ref="recaptcha"></div>
    </Section>
</template>

<script lang="ts" src="./RegisterLicenseePsypact.ts"></script>
<style scoped lang="less" src="./RegisterLicenseePsypact.less"></style>
