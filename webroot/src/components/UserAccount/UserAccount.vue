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
                    :title="$t('compact.confirmSaveCompactTitle')"
                    :showActions="false"
                    @keydown.tab="focusTrapEmailVerificationModal($event)"
                    @keyup.esc="closeEmailVerificationModal"
                >
                    <template v-slot:content>
                        <div class="modal-content confirm-modal-content">
                            {{ $t('common.cannotBeUndone') }}
                            <InputText
                                :formInput="formData.emailVerificationCode"
                                class="verification-code-input-container"
                            />
                            <div class="action-button-row">
                                <InputButton
                                    id="confirm-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeEmailVerificationModal"
                                />
                                <InputSubmit
                                    :formInput="formData.submitEmailVerification"
                                    @click="submitEmailVerificationModal"
                                    class="action-button submit-button continue-button"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('common.submit')"
                                    :isTransparent="true"
                                    :isEnabled="!isFormLoading"
                                />
                            </div>
                        </div>
                    </template>
                </Modal>
            </TransitionGroup>
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
