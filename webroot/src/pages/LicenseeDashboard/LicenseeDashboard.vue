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
                label="+ Obtain Privileges"
                aria-label="obtatin privilege"
                class="obtain-priv-btn"
                @click="startPrivPurchaseFlow"
            />
        </div>
        <div class="home-state-list">
            <HomeStateBlock
                v-for="state in homeStateList"
                :key="state.id"
            />
        </div>
        <LicenseePrivilegeList />
        <AdverseActionList />

    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
