<!--
    AuthCallback.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <Section class="auth-callback-container">
        <Card v-if="isError" class="auth-error-container">
            <div class="auth-error-message">{{ $t('serverErrors.loginError') }}</div>
            <div class="auth-error-message">
                {{ $t('serverErrors.loginErrorActionPart1') }}
                <router-link :to="{ name: 'Login' }">{{ $t('serverErrors.loginErrorActionPart2') }}</router-link>.
            </div>
        </Card>
    </Section>
</template>

<script lang="ts" src="./AuthCallback.ts"></script>
<style scoped lang="less" src="./AuthCallback.less"></style>
