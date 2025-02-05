<!--
    Login.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="login-container">
        <a
            v-if="!isUsingMockApi"
            :href="hostedLoginUriStaff"
            class="login-link"
            rel="noopener noreferrer"
        >
            {{ $t('navigation.loginAsStaff') }}
        </a>
        <a
            v-if="!isUsingMockApi"
            :href="hostedLoginUriLicensee"
            class="login-link"
            rel="noopener noreferrer"
        >
            {{ $t('navigation.loginAsProvider') }}
        </a>
        <InputButton
            v-if="isUsingMockApi"
            label="Mock Staff Login"
            aria-label="Mock Login"
            :isTextLike="true"
            @click="mockStaffLogin"
        />
        <InputButton
            v-if="isUsingMockApi"
            label="Mock Licensee Login"
            aria-label="Mock Licensee Login"
            :isTextLike="true"
            @click="mockLicenseeLogin"
        />
        <router-link
            :to="{ name: 'RegisterLicensee' }"
            class="login-link"
            tabindex="0"
        >
            {{ $t('navigation.registerAsProvider') }}
        </router-link>
    </div>
</template>

<script lang="ts" src="./Login.ts"></script>
<style scoped lang="less" src="./Login.less"></style>
