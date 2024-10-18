<!--
    UserRowEdit.vue
    CompactConnect

    Created by InspiringApps on 10/14/2024.
-->

<template>
    <Card class="edit-user-container">
        <div class="edit-user-title">{{ $t('account.editUserPermissions') }}</div>
        <form @submit.prevent="handleSubmit">
            <div class="edit-user-name">
                {{ user.getFullName() }}
            </div>
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
            <div v-if="userCompactPermission" class="edit-user-form-row">
                <button
                    class="add-state text-like"
                    @click.prevent="createNewStatePermission"
                    @keyup.enter.prevent="createNewStatePermission"
                >+ {{ $t('account.addState') }}</button>
            </div>
            <div class="edit-user-form-row">
                <InputButton
                    class="edit-user-button"
                    :label="$t('common.cancel')"
                    :shouldHideMargin="true"
                    :isTransparent="true"
                    :onClick="handleCancel"
                />
                <InputSubmit
                    class="edit-user-button"
                    :formInput="formData.submit"
                    :label="$t('common.saveChanges')"
                    :isEnabled="!isFormLoading && userCompactPermission"
                />
            </div>
        </form>
    </Card>
</template>

<script lang="ts" src="./UserRowEdit.ts"></script>
<style scoped lang="less" src="./UserRowEdit.less"></style>
