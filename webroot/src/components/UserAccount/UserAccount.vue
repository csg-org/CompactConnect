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
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                />
            </form>
            <ChangePassword />
        </Card>
    </div>
</template>

<script lang="ts" src="./UserAccount.ts"></script>
<style scoped lang="less" src="./UserAccount.less"></style>
