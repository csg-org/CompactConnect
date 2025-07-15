<!--
    UserAccount.vue
    CompactConnect

    Created by InspiringApps on 11/4/2024.
-->

<template>
    <div class="account-area-container">
        <h1 class="card-title">{{ $t('account.accountTitle') }}</h1>
        <Card class="account-area">
            <form @submit.prevent.stop="handleSubmit">
                <InputText :formInput="formData.firstName" />
                <InputText :formInput="formData.lastName" />
                <InputText :formInput="formData.email" />
                <InputSubmit
                    :formInput="formData.submitUserUpdate"
                    class="account-submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                />
            </form>
            <TransitionGroup>
                <Modal
                    v-if="isEmailVerificationModalDisplayed"
                    class="confirm-email-modal"
                    :title="(!isEmailVerificationModalSuccess) ? $t('account.enterVerificationCode') : ' '"
                    :showActions="false"
                    @keydown.tab="focusTrapEmailVerificationModal($event)"
                    @keyup.esc="closeEmailVerificationModal"
                >
                    <template v-slot:content>
                        <div class="modal-content confirm-modal-content">
                            <template v-if="!isEmailVerificationModalSuccess">
                                <div class="confirm-email-subtext">
                                    {{ $t('account.enterVerificationCodeSubtext') }}
                                </div>
                                <InputText
                                    :formInput="formData.emailVerificationCode"
                                    class="verification-code-input-container"
                                />
                            </template>
                            <div v-else class="verification-code-success">
                                <div class="icon-container"><CheckCircleIcon /></div>
                                {{ $t('account.emailUpdateSuccess') }}
                            </div>
                            <div v-if="emailVerificationErrorMessage" class="modal-error">
                                {{ emailVerificationErrorMessage }}
                            </div>
                            <div class="action-button-row">
                                <InputSubmit
                                    v-if="!isEmailVerificationModalSuccess"
                                    :formInput="formData.submitEmailVerification"
                                    @click="submitEmailVerification"
                                    class="action-button submit-button continue-button"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('common.submit')"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputButton
                                    v-if="!isEmailVerificationModalSuccess"
                                    id="confirm-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeEmailVerificationModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    v-if="isEmailVerificationModalSuccess"
                                    :formInput="formData.submitEmailVerification"
                                    @click="closeEmailVerificationModal"
                                    class="action-button submit-button continue-button"
                                    :label="$t('common.close')"
                                />
                            </div>
                        </div>
                    </template>
                </Modal>
            </TransitionGroup>
            <UpdateHomeJurisdiction v-if="isLicensee" />
            <ChangePassword />
            <section
                v-if="isLicensee && currentCompactType"
                class="military-status-container"
                aria-labelledby="military-status-title"
            >
                <h2 class="section-title" id="military-status-title">
                    {{ $t('military.militaryStatusTitle') }}
                </h2>
                <div class="btn-container military-status-btn">
                    <InputButton
                        :label="`${this.$t('common.add')}/${this.$t('common.edit')}`"
                        class="btn view-military-btn"
                        @click="viewMilitaryStatus"
                    />
                </div>
            </section>
        </Card>
    </div>
</template>

<script lang="ts" src="./UserAccount.ts"></script>
<style scoped lang="less" src="./UserAccount.less"></style>
