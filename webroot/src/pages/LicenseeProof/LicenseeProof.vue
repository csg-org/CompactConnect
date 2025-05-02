<!--
    LicenseeProof.vue
    CompactConnect

    Created by InspiringApps on 5/2/2025.
-->

<template>
    <div class="licensee-verification-container">
        <div class="print-header">
            <div class="app-logo">App logo</div>
            <div class="current-date">Current date</div>
        </div>
        <div class="page-title">{{ $t('licensing.privilegeVerification') }}</div>
        <div class="licensee-container">
            <LicenseHomeIcon class="icon provider-icon" />
            {{ $t('licensing.practitionerInformation') }}
        </div>
        <div class="licenses-container">
            <LicenseHomeIcon class="icon licenses-icon" />
            {{ $t('licensing.homeStateLicenses') }}
        </div>
        <div class="privileges-container">
            <PrivilegesIcon class="icon privileges-icon" />
            {{ $t('licensing.privileges') }}
        </div>
        <div class="print-footer">Print footer</div>
    </div>
</template>

<script lang="ts" src="./LicenseeProof.ts"></script>
<style scoped lang="less" src="./LicenseeProof.less"></style>
