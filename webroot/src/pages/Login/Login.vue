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
        <InputButton
            label="Mock Staff Login"
            aria-label="Mock Login"
            :isTextLike="true"
            @click="mockStaffLogin"
        />
        <InputButton
            label="Mock Licensee Login"
            aria-label="Mock Licensee Login"
            :isTextLike="true"
            @click="mockLicenseeLogin"
        />
    </div>
</template>

<script lang="ts" src="./Login.ts"></script>
<style scoped lang="less" src="./Login.less"></style>
