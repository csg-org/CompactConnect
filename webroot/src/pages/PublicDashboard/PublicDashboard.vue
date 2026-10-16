<!--
    PublicDashboard.vue
    CompactConnect

    Created by InspiringApps on 8/12/2024.
-->

<template>
    <div class="login-container">
        <div class="dashboard-splash-container">
            <template v-if="$isAppModePsyPact">
                <div class="splash-image-container psypact" aria-hidden="true">
                    <svg viewBox="0 0 698 981" class="splash-image psypact">
                        <path fill-rule="evenodd" clip-rule="evenodd" d="M-405.934 30.1602L-405.377 59.7573L-387.263
                            62.1804C-377.3 63.5137 -363.99 66.5361 -357.686 68.895C-330.992 78.8813 -327.166 94.4883
                            -325.054 201.971C-322.991 306.924 -325.054 349.085 -279.926 458.67C-214.732 546.338
                            -157.121 594.444 -58.0225 619.795C-38.3233 624.835 7.34122 631.555 33.5117 633.267L63.7181
                            634.616V878.298C63.0625 958.173 62.795 963.412 58.8214 973.957C48.2458 1002.04 40.003
                            1010.62 16.0868 1018.47C5.03867 1022.09 -3.2323 1022.95 -33.855 1023.67L-70.5547
                            1024.52V1055.49V1086.47H148.638H367.831V1055.3V1024.13H335.713C298.142 1024.13 278.364
                            1020.64 262.673 1011.22C243.537 999.732 232.093 983.763 232.093
                            958.778V796.897V635.016L255.707 633.538C351.611 627.539 432.74 605.497 508.248
                            540.91C525.393 526.248 548.629 500.599 559.438 484.407C599.323 424.642 614.214 318.038
                            618.11 246.632C618.826 233.509 620.191 195.558 621.142 162.295C622.423 117.506 623.622
                            100.022 625.763 94.8965C631.547 81.0552 653.13 67.5074 676.512 63.0391C700.359 58.4823
                            697.626 62.836 697.626 29.402V0L669.976 1.15629C624.621 3.0506 578.265 16.343 548.038
                            36.1226C517.814 55.9003 487.165 92.777 472.779 126.679C464.202 146.889 450.809 205.832
                            450.809 256.77C446.977 465.003 392.563 488.547 318.678 529.486C298.06 540.91 231.087
                            554.126 231.087 545.598C231.087 457.843 231.087 351.295 231.087 291.903V222.012C231.087
                            148.291 232.068 136.949 240.368 114.829C251.836 84.2526 279.068 73.1803 343.197
                            73.0194L367.831 72.9571V41.7874V10.6178H148.638H-70.5547V41.7874V72.9571L-46.9261
                            73.0194C12.073 73.1743 40.1619 83.4965 53.0038 109.743C62.4673 129.087 64.1062 143.22
                            64.1444 205.832L64.1786 263.295L63.7181 550.035C38.4997 545.165 12.9099 542.135 -11.624
                            534.202C-26.7805 529.303 -54.9699 515.568 -59.8686 510.698C-136.798 446.17 -146.773 360.049
                            -154.104 266.008C-162.98 152.098 -181.155 99.5961 -226.292 57.4708C-245.051 39.9635
                            -258.486 31.1797 -279.725 22.5367C-310.652 9.95016 -357.808 0.563065
                            -390.104 0.563065H-406.489L-405.934 30.1602Z" />
                    </svg>
                </div>
                <div class="splash-title-container psypact">
                    <div class="splash-title">{{ $t('compact.welcomeTo') }}</div>
                    <div class="splash-title">{{ $t('common.appNamePsyPact') }}</div>
                </div>
            </template>
            <template v-else>
                <div class="splash-image-container upper" aria-hidden="true">
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
                <div class="splash-image-container lower" aria-hidden="true">
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
            </template>
        </div>
        <div class="dashboard-content-container">
            <div class="dashboard-content">
                <div class="dashboard-logo-container">
                    <img
                        v-if="$isAppModePsyPact"
                        src="@assets/logos/psypact-logo.png"
                        class="dashboard-logo"
                        :alt="$t('common.appNamePsyPact')"
                    />
                    <img
                        v-else
                        src="@assets/logos/compact-connect-logo.png"
                        class="dashboard-logo"
                        :alt="$t('common.appName')"
                    />
                </div>
                <AppTypeSelector v-if="isAppTypeSelectorEnabled" />
                <Card class="dashboard-card provider-login-card">
                    <div class="header">
                        <LicenseeUserIcon class="login-icon" />
                        <div class="title-container">
                            <div class="title">{{ $t('navigation.loginAsProvider') }}</div>
                            <div v-if="$isAppModePsyPact" class="title-subtext">
                                {{ $t('navigation.loginAsProviderSubtextPsyPact') }}
                            </div>
                            <div v-else class="title-subtext">{{ $t('navigation.loginAsProviderSubtext') }}</div>
                        </div>
                    </div>
                    <a
                        v-if="!isUsingMockApi"
                        :href="licenseeLoginUri($appMode)"
                        class="login-link"
                        rel="noopener noreferrer"
                    >
                        {{ $t('navigation.login') }}
                    </a>
                    <div
                        v-else
                        class="login-link"
                        @click="mockLicenseeLogin($appMode)"
                        @keyup.enter="mockLicenseeLogin($appMode)"
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
                            <div v-if="!$isAppModePsyPact" class="title-subtext">
                                {{ $t('navigation.loginAsStaffSubtext') }}
                            </div>
                        </div>
                    </div>
                    <template v-if="$isAppModePsyPact">
                        <a
                            v-if="!isUsingMockApi"
                            :href="staffLoginUri($appMode)"
                            class="login-link staff"
                            rel="noopener noreferrer"
                            @click="setGotoCompact(compactTypes.PSYPACT)"
                        >
                            {{ $t('navigation.login') }}
                        </a>
                        <div
                            v-else
                            class="login-link staff"
                            @click="bypassToStaffLogin($appMode, compactTypes.PSYPACT)"
                            @keyup.enter="bypassToStaffLogin($appMode, compactTypes.PSYPACT)"
                            tabindex="0"
                            role="button"
                            :aria-label="$t('navigation.login')"
                        >
                            {{ $t('navigation.login') }}
                        </div>
                    </template>
                    <div v-else class="staff-compacts">
                        <template v-for="compact in $compactsEnabledCompactConnect" :key="compact.type">
                            <a
                                v-if="!isUsingMockApi"
                                :href="staffLoginUri(compact.appMode)"
                                class="login-link small"
                                rel="noopener noreferrer"
                                @click="setGotoCompact(compact.type)"
                            >
                                {{ getCompactDisplay(compact) }}
                            </a>
                            <div
                                v-else
                                class="login-link small"
                                @click="bypassToStaffLogin(compact.appMode, compact.type)"
                                @keyup.enter="bypassToStaffLogin(compact.appMode, compact.type)"
                                tabindex="0"
                                role="button"
                                :aria-label="getCompactDisplay(compact)"
                            >
                                {{ getCompactDisplay(compact) }}
                            </div>
                        </template>
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
            </div>
            <div class="dashboard-footer">
                <router-link :to="{ name: 'MfaResetStartLicensee' }" class="footer-link">
                    {{ $t('account.lockedOut') }}
                </router-link>
                <router-link :to="{ name: 'PrivacyPolicy' }" class="footer-link">
                    {{ $t('privacyPolicy.title') }}
                </router-link>
                <a
                    v-if="!$isAppModePsyPact"
                    href="https://compactconnect.org/?page_id=399"
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
