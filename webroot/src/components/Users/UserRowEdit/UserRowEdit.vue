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
                    :isEnabled="!isFormLoading"
                />
            </div>
        </form>
    </Card>
</template>

<script lang="ts" src="./UserRowEdit.ts"></script>
<style scoped lang="less" src="./UserRowEdit.less"></style>
