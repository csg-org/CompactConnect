<!--
    LicenseeDashboard.vue
    CompactConnect

    Created by InspiringApps on 9/23/2024.
-->

<template>
    <div class="licensee-dashboard-container">
        <div class="top-block">
            <h2 class="welcome-user">Welcome, {{ userFullName }}</h2>
            <InputButton
                :label="obtainPrivButtonLabel"
                aria-label="obtatin privilege"
                class="obtain-priv-btn"
                @click="startPrivPurchaseFlow"
            />
        </div>
        <div class="home-state-list">
            <HomeStateBlock
                v-for="(state, i) in homeStateList"
                :key="state.abbrev+i"
                :state="state"
            />
        </div>
        <LicenseCard
            v-for="(license, index) in licenseList"
            :key="license.type+index"
            :license="license"
        />
        <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="privilege-logo-container">
                    <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                </div>
                <div class="privilege-title">
                    {{privilegeTitle}}
                </div>
            </div>
            <PrivilegeCard
                v-for="(privilege, index) in privilegeList"
                :key="privilege.type+index"
                :privilege="privilege"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
