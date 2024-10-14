<!--
    LicenseeDashboard.vue
    CompactConnect

    Created by InspiringApps on 9/23/2024.
-->

<template>
    <div class="licensee-dashboard-container">
        <div class="top-block">
            <div class="welcome-user">{{welcomeText}}, {{ userFullName }}</div>
            <InputButton
                :label="obtainPrivButtonLabel"
                aria-label="obtatin privilege"
                class="obtain-priv-btn"
                :isEnabled="!isPrivilegePurchaseDisabled"
                @click="startPrivPurchaseFlow"
            />
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
                v-for="(license, index) in licenseList"
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
                <div class="privilege-logo-container">
                    <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                </div>
                <div class="privilege-title">
                    {{privilegeTitle}}
                </div>
            </div>
            <div class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in privilegeList"
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
