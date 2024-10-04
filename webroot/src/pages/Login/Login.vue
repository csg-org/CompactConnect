<!--
    Login.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="login-container">
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
</template>

<script lang="ts" src="./Login.ts"></script>
<style scoped lang="less" src="./Login.less"></style>
