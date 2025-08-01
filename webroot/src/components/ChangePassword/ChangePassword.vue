<!--
    ChangePassword.vue
    CompactConnect

    Created by InspiringApps on 11/4/2024.
-->

<template>
    <div class="change-password-container">
        <div class="form-title">{{ $t('common.changePassword') }}</div>
        <form @submit.prevent="handleSubmit">
            <label for="username" class="hidden">{{ $t('common.username') }}</label>
            <input
                type="text"
                id="username"
                class="hidden"
                autocomplete="username"
                :value="userAppEmail"
                :disabled="true"
            />
            <InputPassword
                :formInput="formData.currentPassword"
                :joiMessages="joiMessages"
                :showEyeIcon="true"
            />
            <InputPassword
                :formInput="formData.newPassword"
                :joiMessages="joiMessages"
                :showEyeIcon="true"
                @input="validateNewPassword"
            />
            <InputPassword
                :formInput="formData.confirmPassword"
                :joiMessages="joiMessages"
                :showEyeIcon="true"
                @input="validateNewPassword"
                @blur="validateNewPassword"
            />
            <InputSubmit
                :formInput="formData.submit"
                :label="submitLabel"
                :isEnabled="!isFormLoading"
            />
        </form>
    </div>
</template>

<script lang="ts" src="./ChangePassword.ts"></script>
<style scoped lang="less" src="./ChangePassword.less"></style>
