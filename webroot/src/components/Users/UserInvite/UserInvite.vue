<!--
    UserInvite.vue
    CompactConnect

    Created by InspiringApps on 11/11/2024.
-->

<template>
    <Card class="invite-user-container">
        <div class="invite-user-title">{{ $t('account.inviteNewUser') }}</div>
        <MockPopulate :isEnabled="isMockPopulateEnabled" @selected="mockPopulate" />
        <form @submit.prevent="handleSubmit">
            <div class="invite-user-form-row">
                <InputText :formInput="formData.email" class="invite-email" />
            </div>
            <div class="invite-user-form-row">
                <InputSelect :formInput="formData.compact" class="permission-type-select" />
                <div class="input-connector"></div>
                <InputSelect :formInput="formData.compactPermission" class="permission-select" />
            </div>
            <TransitionGroup name="fade">
                <div
                    v-for="(formInput, index) in permissionStateInputs"
                    :key="formInput.id"
                    class="invite-user-form-row"
                >
                    <div v-if="index === 0" class="row-separator"></div>
                    <InputSelect :formInput="formData[`state-option-${index}`]" class="permission-type-select" />
                    <div class="input-connector"></div>
                    <InputSelect :formInput="formInput" class="permission-select" />
                </div>
            </TransitionGroup>
            <div v-if="shouldShowAddStateButton" class="invite-user-form-row">
                <button
                    class="add-state text-like"
                    @click.prevent="createNewStatePermission"
                    @keyup.enter.prevent="createNewStatePermission"
                >+ {{ $t('account.addState') }}</button>
            </div>
            <div class="invite-user-form-row">
                <InputButton
                    class="invite-user-button"
                    :label="$t('common.cancel')"
                    :shouldHideMargin="true"
                    :isTransparent="true"
                    :onClick="handleCancel"
                />
                <InputSubmit
                    class="invite-user-button"
                    :formInput="formData.submit"
                    :label="$t('common.sendInvite')"
                    :isEnabled="!isFormLoading && isAnyTypeOfAdmin"
                />
            </div>
        </form>
    </Card>
</template>

<script lang="ts" src="./UserInvite.ts"></script>
<style scoped lang="less" src="./UserInvite.less"></style>
