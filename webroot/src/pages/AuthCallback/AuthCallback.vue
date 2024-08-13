<!--
    AuthCallback.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div v-if="isError" class="auth-error-container">
        <p>There was an error logging you in.</p>
        <p>You can <router-link :to="{ name: 'Login' }">try logging in again</router-link>.</p>
    </div>
    <div v-else class="auth-loading-container">
        <p>Logging in...</p>
    </div>
</template>

<script lang="ts" src="./AuthCallback.ts"></script>
<style scoped lang="less" src="./AuthCallback.less"></style>
