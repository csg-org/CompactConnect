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
                    :isEnabled="!isPrivilegePurchaseDisabled"
                    @click="startPrivPurchaseFlow"
                />
            </div>
        </div>
        <div class="license-section">
            <div class="home-state-section">
                <div class="home-state-list">
                    <HomeStateBlock
                        v-for="(state, i) in homeStateList"
                        :key="'state'+i"
                        :state="state"
                        class="no-touch-item"
                    />
                </div>
                <div v-if="hasMoreThanOneActiveLicense" class="homestate-error-text">
                    {{twoHomeStateErrorText}}
                </div>
            </div>
            <div
                v-for="(license, index) in licenseeLicenses"
                :key="'license'+index"
                class="no-touch-item license-chunk"
            >
                <LicenseCard
                    :license="license"
                />
                <div v-if="!checkIfLicenseActive(license)" class="license-expired-message">
                    {{licenseExpiredMessage}}
                </div>
            </div>
        </div>
        <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
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
                    :key="'privilege'+index"
                    :privilege="privilege"
                    class="no-touch-item"
                />
            </div>
        </div>
         <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                    </div>
                    <div class="title-text">
                        {{pastPrivilegesTitle}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="togglePastPrivsCollapsed"
                />
            </div>
            <div v-if="!isPastPrivsCollapsed" class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in pastPrivilegeList"
                    :key="'privilege'+index"
                    :privilege="privilege"
                    class="no-touch-item"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
