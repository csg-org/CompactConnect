<!--
    UserAccount.vue
    CompactConnect

    Created by InspiringApps on 11/4/2024.
-->

<template>
    <div class="account-area-container">
        <h1 class="card-title">{{ $t('account.accountTitle') }}</h1>
        <Card class="account-area">
            <form @submit.prevent="handleSubmit">
                <InputText :formInput="formData.firstName" />
                <InputText :formInput="formData.lastName" />
                <InputText :formInput="formData.email" />
                <InputSubmit
                    :formInput="formData.submit"
                    class="account-submit"
                    :class="{ 'not-visible': !isSubmitVisible }"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                    :tabindex="(isSubmitVisible) ? 0 : -1"
                />
            </form>
            <ChangePassword />
        </Card>
    </div>
</template>

<script lang="ts" src="./UserAccount.ts"></script>
<style scoped lang="less" src="./UserAccount.less"></style>
