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
        <div class="license-section">
            <div class="home-state-list">
                <HomeStateBlock
                    v-for="(state, i) in homeStateList"
                    :key="'state'+i"
                    :state="state"
                    class="no-touch-item"
                />
                <div v-if="hasTwoActiveLicenses" class="red">
                    Oh no
                </div>
            </div>
            <LicenseCard
                v-for="(license, index) in licenseList"
                :key="'license'+index"
                :license="license"
                class="no-touch-item"
            />
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
                    :key="'priv'+index"
                    :privilege="privilege"
                    class="no-touch-item"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
