<!--
    LicenseeDashboard.vue
    CompactConnect

    Created by InspiringApps on 9/23/2024.
-->

<template>
    <div class="licensee-dashboard-container">
        <div class="top-block">
            <div class="welcome-user">{{welcomeText}}, {{ userFullName }}</div>
            <div class="button-block">
                <InputButton
                    :label="$t('military.viewMilitaryStatus')"
                    :aria-label="$t('military.viewMilitaryStatus')"
                    :isTransparent="true"
                    class="view-military-btn"
                    @click="viewMilitaryStatus"
                />
                <InputButton
                    :label="obtainPrivButtonLabel"
                    :aria-label="$t('licensing.obtainPrivileges')"
                    class="obtain-priv-btn"
                    :isEnabled="isPrivilegePurchaseEnabled"
                    @click="startPrivPurchaseFlow"
                />
            </div>
        </div>
        <div class="license-section">
            <HomeStateBlock
                v-if="homeJurisdiction"
                :state="homeJurisdiction"
                class="no-touch-item"
            />
            <div
                v-for="(license, index) in licenseeLicenses"
                :key="'license'+index"
                class="no-touch-item license-chunk"
            >
                <LicenseCard
                    :license="license"
                    :homeState="homeJurisdiction"
                    :shouldIncludeLogo="true"
                />
                <div v-if="!isLicenseActive(license)" class="license-expired-message">
                    {{licenseExpiredMessage}}
                </div>
            </div>
        </div>
        <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img
                            class="home-state-img"
                            src="@assets/icons/ico-privilege.svg"
                            :alt="$t('licensing.privilegeIcon')"
                        />
                    </div>
                    <div class="title-text">
                        {{privilegeTitle}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="togglePrivsCollapsed"
                />
            </div>
            <div v-if="!isPrivsCollapsed" class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in licenseePrivileges"
                    :key="index"
                    :privilege="privilege"
                    :licensee="licensee"
                    class="no-touch-item"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
