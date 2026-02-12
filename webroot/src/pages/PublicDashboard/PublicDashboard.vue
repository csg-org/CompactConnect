<!--
    PublicDashboard.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="login-container">
        <div class="dashboard-splash-container">
            <div class="splash-image-container upper">
                <svg viewBox="0 0 535 217" class="splash-image upper">
                    <path d="M164.026 208.904L164.026 216.404L164.026 208.904ZM552.708 -96.6482C556.85
                        -96.6482 560.208 -100.006 560.208 -104.148C560.208 -108.29 556.85 -111.648 552.708
                        -111.648L552.708 -104.148L552.708 -96.6482ZM534.716 208.904L534.716 201.404L164.026
                        201.404L164.026 208.904L164.026 216.404L534.716 216.404L534.716 208.904ZM164.026
                        -104.148L164.026 -96.6483L552.708 -96.6482L552.708 -104.148L552.708 -111.648L164.026
                        -111.648L164.026 -104.148ZM7.49995 52.3777L15 52.3777C15 -29.9271 81.7212 -96.6483 164.026
                        -96.6483L164.026 -104.148L164.026 -111.648C73.4369 -111.648 -3.94317e-05 -38.2114
                        -4.73512e-05 52.3777L7.49995 52.3777ZM7.49995 52.3777L-4.73512e-05 52.3777C-5.52708e-05
                        142.967 73.437 216.404 164.026 216.404L164.026 208.904L164.026 201.404C81.7213 201.404
                        14.9999 134.683 15 52.3777L7.49995 52.3777Z"
                    />
                </svg>
            </div>
            <div class="splash-image-container lower">
                <svg viewBox="0 0 721 332" class="splash-image lower">
                    <path d="M-126.192 7.5H472.073C605.133 7.5 713 115.367 713 248.427C713 381.487 605.133
                        489.354 472.073 489.354H-126.192"
                        stroke-width="15" stroke-linecap="round"
                    />
                </svg>
            </div>
            <div class="splash-title-container">
                <div class="splash-title">{{ $t('compact.welcomeTo') }}</div>
                <div class="splash-title">{{ $t('common.appName') }}</div>
            </div>
        </div>
        <div class="dashboard-content-container">
            <div class="dashboard-logo-container">
                <img
                    src="@assets/logos/compact-connect-logo.png"
                    class="dashboard-logo"
                    :alt="$t('common.appName')"
                />
            </div>
            <Card class="dashboard-card provider-login-card">
                <div class="header">
                    <LicenseeUserIcon class="login-icon" />
                    <div class="title-container">
                        <div class="title">{{ $t('navigation.loginAsProvider') }}</div>
                        <div class="title-subtext">{{ $t('navigation.loginAsProviderSubtext') }}</div>
                    </div>
                </div>
                <a
                    v-if="!isUsingMockApi"
                    :href="hostedLoginUriLicensee"
                    class="login-link"
                    rel="noopener noreferrer"
                >
                    {{ $t('navigation.login') }}
                </a>
                <div
                    v-else
                    class="login-link"
                    @click="mockLicenseeLogin"
                    @keyup.enter="mockLicenseeLogin"
                    tabindex="0"
                    role="button"
                    :aria-label="$t('navigation.login')"
                >
                    {{ $t('navigation.login') }}
                </div>
                <div class="separator" />
                {{ $t('navigation.registerAsProviderSubtext') }}
                <router-link
                    :to="{ name: 'RegisterLicensee' }"
                    class="login-link register transparent"
                    tabindex="0"
                >
                    {{ $t('navigation.registerAsProvider') }}
                </router-link>
            </Card>
            <Card class="dashboard-card staff-login-card">
                <div class="header">
                    <StaffUserIcon class="login-icon" />
                    <div class="title-container">
                        <div class="title">{{ $t('navigation.loginAsStaff') }}</div>
                        <div class="title-subtext">{{ $t('navigation.loginAsStaffSubtext') }}</div>
                    </div>
                </div>
                <div class="staff-compacts">
                    <a
                        v-if="!isUsingMockApi"
                        :href="hostedLoginUriStaff"
                        class="login-link small"
                        rel="noopener noreferrer"
                    >
                        {{ getCompactDisplay(compactTypes.ASLP) }}
                    </a>
                    <div
                        v-else
                        class="login-link small"
                        @click="bypassToStaffLogin"
                        @keyup.enter="bypassToStaffLogin"
                        tabindex="0"
                        role="button"
                        :aria-label="getCompactDisplay(compactTypes.ASLP)"
                    >
                        {{ getCompactDisplay(compactTypes.ASLP) }}
                    </div>
                    <a
                        v-if="!isUsingMockApi"
                        :href="hostedLoginUriStaff"
                        class="login-link small"
                        rel="noopener noreferrer"
                    >
                        {{ getCompactDisplay(compactTypes.OT) }}
                    </a>
                    <div
                        v-else
                        class="login-link small"
                        @click="bypassToStaffLogin"
                        @keyup.enter="bypassToStaffLogin"
                        tabindex="0"
                        role="button"
                        :aria-label="getCompactDisplay(compactTypes.OT)"
                    >
                        {{ getCompactDisplay(compactTypes.OT) }}
                    </div>
                    <a
                        v-if="!isUsingMockApi"
                        :href="hostedLoginUriStaff"
                        class="login-link small"
                        rel="noopener noreferrer"
                    >
                        {{ getCompactDisplay(compactTypes.COUNSELING) }}
                    </a>
                    <div
                        v-else
                        class="login-link small"
                        @click="bypassToStaffLogin"
                        @keyup.enter="bypassToStaffLogin"
                        tabindex="0"
                        role="button"
                        :aria-label="getCompactDisplay(compactTypes.COUNSELING)"
                    >
                        {{ getCompactDisplay(compactTypes.COUNSELING) }}
                    </div>
                    <a
                        v-if="!isUsingMockApi"
                        :href="hostedLoginUriStaffCosmo"
                        class="login-link small"
                        rel="noopener noreferrer"
                    >
                        {{ getCompactDisplay(compactTypes.COSMETOLOGY) }}
                    </a>
                    <div
                        v-else
                        class="login-link small"
                        @click="bypassToStaffLoginCosmo"
                        @keyup.enter="bypassToStaffLoginCosmo"
                        tabindex="0"
                        role="button"
                        :aria-label="getCompactDisplay(compactTypes.COSMETOLOGY)"
                    >
                        {{ getCompactDisplay(compactTypes.COSMETOLOGY) }}
                    </div>
                </div>
            </Card>
            <Card class="dashboard-card privilege-search">
                <div class="header">
                    <SearchIcon class="login-icon" />
                    <div class="title-container">
                        <div class="title">{{ $t('navigation.verifyPrivilege') }}</div>
                        <div class="title-subtext">{{ $t('navigation.verifyPrivilegeSubtext') }}</div>
                    </div>
                </div>
                <router-link
                    :to="{ name: 'LicneseeSearchPublic' }"
                    class="login-link transparent"
                    tabindex="0"
                >
                    {{ $t('navigation.verifyPrivilegeSearch') }}
                </router-link>
            </Card>
            <div class="dashboard-footer">
                <router-link :to="{ name: 'MfaResetStartLicensee' }" class="footer-link">
                    {{ $t('account.lockedOut') }}
                </router-link>
                <router-link :to="{ name: 'PrivacyPolicy' }" class="footer-link">
                    {{ $t('privacyPolicy.title') }}
                </router-link>
                <a
                    href="https://compactconnect.zendesk.com/hc/en-us"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="footer-link"
                >
                    {{ $t('navigation.helpCenter') }}
                </a>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PublicDashboard.ts"></script>
<style scoped lang="less" src="./PublicDashboard.less"></style>
