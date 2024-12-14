<!--
    Login.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div v-if="!isUsingMockApi" class="login-container">
        <a
            :href="hostedLoginUriStaff"
            class="login-link"
        >
            Login as Staff
        </a>
        <a
            :href="hostedLoginUriLicensee"
            class="login-link"
        >
            Login as Provider
        </a>
    </div>
    <div v-else class="login-container">
        <router-link
            :to="{ name: 'Home' }"
            class="login-link"
            @click.prevent="setMockAuthTokens"
        >
            Mock Login
        </router-link>
    </div>
</template>

<script lang="ts" src="./Login.ts"></script>
<style scoped lang="less" src="./Login.less"></style>
