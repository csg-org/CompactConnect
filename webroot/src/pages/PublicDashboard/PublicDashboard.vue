<!--
    PublicDashboard.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="login-container">
        <div class="dashboard-content-container">
            <div class="dashboard-logo-container">
                <img
                    src="@assets/logos/compact-connect-logo.png"
                    class="dashboard-logo"
                    :alt="$t('common.appName')"
                />
            </div>
        <div class="dashboard-row">
            <router-link
                :to="{ name: 'LicneseeSearchPublic' }"
                class="login-link large"
                tabindex="0"
            >
                <SearchIcon class="login-icon" />
                {{ $t('navigation.verifyPrivilege') }}
            </router-link>
        </div>
        <div class="dashboard-row">
            <router-link
                :to="{ name: 'RegisterLicensee' }"
                class="login-link small"
                tabindex="0"
            >
                <RegisterIcon class="login-icon" />
                {{ $t('navigation.registerAsProvider') }}
            </router-link>
            <a
                v-if="!isUsingMockApi"
                :href="hostedLoginUriLicensee"
                class="login-link small"
                rel="noopener noreferrer"
            >
                <LicenseeUserIcon class="login-icon" />
                {{ $t('navigation.loginAsProvider') }}
            </a>
            <div
                v-else
                class="login-link small"
                @click="mockLicenseeLogin"
                @keyup.enter="mockLicenseeLogin"
                tabindex="0"
            >
                <LicenseeUserIcon class="login-icon" />
                {{ $t('navigation.loginAsProvider') }}
            </div>
            <a
                v-if="!isUsingMockApi"
                :href="hostedLoginUriStaff"
                class="login-link small"
                rel="noopener noreferrer"
            >
                <StaffUserIcon class="login-icon" />
                {{ $t('navigation.loginAsStaff') }}
            </a>
            <div
                v-else
                class="login-link small"
                @click="mockStaffLogin"
                @keyup.enter="mockStaffLogin"
                tabindex="0"
            >
                <StaffUserIcon class="login-icon" />
                {{ $t('navigation.loginAsStaff') }}
            </div>
        </div>
        </div>
        <div class="dashboard-footer">
            <router-link :to="{ name: 'MfaResetStartLicensee' }" class="footer-link">
                {{ $t('account.lockedOut') }}
            </router-link>
            <router-link :to="{ name: 'PrivacyPolicy' }" class="footer-link">
                {{ $t('privacyPolicy.title') }}
            </router-link>
        </div>
    </div>
</template>

<script lang="ts" src="./PublicDashboard.ts"></script>
<style scoped lang="less" src="./PublicDashboard.less"></style>
