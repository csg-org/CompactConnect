<!--
    LicenseeDashboard.vue
    CompactConnect

    Created by InspiringApps on 9/23/2024.
-->

<template>
    <div class="licensee-dashboard-container">
        <h2 class="welcome-user">{{ userFullName }}</h2>
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
