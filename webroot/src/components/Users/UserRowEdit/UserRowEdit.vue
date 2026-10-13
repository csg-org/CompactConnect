<!--
    UserRowEdit.vue
    CompactConnect

    Created by InspiringApps on 10/14/2024.
-->

<template>
    <Card class="edit-user-container" @keydown.tab="focusTrap($event)">
        <div v-if="!isFormSuccessful">
            <div class="edit-user-title">{{ $t('account.editUserPermissions') }}</div>
            <form @submit.prevent="handleSubmit">
                <div class="edit-user-name">{{ user.getFullName() }}</div>
                <div class="edit-user-email">{{ user.compactConnectEmail }}</div>
                <div class="edit-user-form-row">
                    <InputSelect :formInput="formData.compact" class="permission-type-select" />
                    <div class="input-connector"></div>
                    <InputSelect :formInput="formData.compactPermission" class="permission-select" />
                </div>
                <TransitionGroup name="fade">
                    <div
                        v-for="(formInput, index) in permissionStateInputs"
                        :key="formInput.id"
                        class="edit-user-form-row"
                    >
                        <div v-if="index === 0" class="row-separator"></div>
                        <InputSelect :formInput="formData[`state-option-${index}`]" class="permission-type-select" />
                        <div class="input-connector"></div>
                        <InputSelect :formInput="formInput" class="permission-select" />
                    </div>
                </TransitionGroup>
                <div v-if="shouldShowAddStateButton" class="edit-user-form-row">
                    <button
                        class="add-state text-like"
                        @click.prevent="createNewStatePermission"
                        @keyup.enter.prevent="createNewStatePermission"
                    >+ {{ $t('account.addState') }}</button>
                </div>
                <div class="edit-user-form-row">
                    <InputButton
                        id="cancel-edit-user"
                        class="edit-user-button"
                        :label="$t('common.cancel')"
                        :shouldHideMargin="true"
                        :isTransparent="true"
                        :onClick="handleCancel"
                    />
                    <InputSubmit
                        class="edit-user-button"
                        :formInput="formData.submit"
                        :label="$t('common.save')"
                        :isEnabled="!isFormLoading && isAnyTypeOfAdmin"
                    />
                </div>
            </form>
        </div>
        <div v-else class="edit-user-success">
            <div class="icon-container">
                <CheckCircle aria-hidden="true" />
            </div>
            <div class="success-title">{{ permissionsUpdatedTitle }}</div>
            <div class="success-subtitle">{{ permissionsUpdatedDescription }}</div>
            <div class="success-actions">
                <InputButton
                    id="continue-without-logout"
                    class="edit-user-button"
                    :label="$t('common.continue')"
                    :shouldHideMargin="true"
                    :isTransparent="true"
                    :onClick="handleContinueWithoutLoggingOut"
                />
                <InputButton
                    v-if="isCurrentUser"
                    id="log-out-edit-user"
                    class="edit-user-button"
                    :label="$t('account.logOut')"
                    :shouldHideMargin="true"
                    :onClick="handleLogout"
                />
            </div>
        </div>
    </Card>
</template>

<script lang="ts" src="./UserRowEdit.ts"></script>
<style scoped lang="less" src="./UserRowEdit.less"></style>
