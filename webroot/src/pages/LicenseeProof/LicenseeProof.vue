<!--
    LicenseeProof.vue
    CompactConnect

    Created by InspiringApps on 5/2/2025.
-->

<template>
    <div class="licensee-verification-container">
        <div class="print-header">
            <div class="app-logo-container">
                <img
                    src="@assets/logos/compact-connect-logo.png"
                    :alt="$t('common.appName')"
                    class="app-logo"
                />
                <div class="page-nav">
                    <router-link
                        v-if="currentCompactType"
                        :to="{ name: 'LicenseeDashboard', params: { compact: currentCompactType }}"
                        class="nav-item text-like"
                    >
                        {{ $t('common.back') }}
                    </router-link>
                    <button
                        class="nav-item text-like"
                        @click="printHandler"
                        @keyup.enter="printHandler"
                    >{{ $t('common.print') }}</button>
                </div>
            </div>
            <div class="current-date">{{ currentDateDisplay }}</div>
        </div>
        <div class="page-title">{{ $t('licensing.privilegeVerification') }}</div>
        <div class="section-container licensee-container">
            <div class="section-title-container">
                <UserIcon class="icon provider-icon" />
                {{ $t('licensing.practitionerInformation') }}
            </div>
            <div class="row highlight">
                <div class="cell">
                    <span class="cell-title">{{ $t('common.name') }}</span>
                    <span>{{ userFullName }}</span>
                </div>
                <div class="cell max-gap">
                    <span class="cell-title">{{ $t('licensing.homeState') }}</span>
                    <span>{{ homeJurisdictionName }}</span>
                </div>
            </div>
        </div>
        <div class="section-container licenses-container">
            <div class="section-title-container">
                <LicenseHomeIcon class="icon licenses-icon" />
                {{ $t('licensing.homeStateLicenses') }}
            </div>
            <div
                v-for="(license, index) in licenseeLicenses"
                :key="'license'+index"
                class="row"
            >
                <div class="cell">
                    <span>{{ license.displayName(', ') }}</span>
                </div>
                <div class="cell max-gap">
                    <span class="cell-title">{{ $t('licensing.activeDate') }}</span>
                    <span class="date-text">{{ license.issueDateDisplay() }}</span>
                </div>
                <div class="cell">
                    <span class="cell-title">{{ $t('licensing.expiration') }}</span>
                    <span class="date-text">{{ license.expireDateDisplay() }}</span>
                </div>
            </div>
        </div>
        <div class="section-container privileges-container">
            <div class="section-title-container">
                <PrivilegesIcon class="icon privileges-icon" />
                {{ $t('licensing.privileges') }}
            </div>
            <div
                v-for="(privilege, index) in licenseePrivileges"
                :key="`privilege${index}`"
                class="row"
            >
                <div class="cell">
                    <span>{{ privilege.displayName(', ') }}</span>
                </div>
                <div class="cell max-gap">
                    <span class="cell-title">{{ $t('licensing.activeDate') }}</span>
                    <span class="date-text">{{ privilege.issueDateDisplay() }}</span>
                </div>
                <div class="cell">
                    <span class="cell-title">{{ $t('licensing.expiration') }}</span>
                    <span class="date-text">{{ privilege.expireDateDisplay() }}</span>
                </div>
            </div>
        </div>
        <div class="print-footer">{{ $t('licensing.privilegeProofFooter') }}</div>
    </div>
</template>

<script lang="ts" src="./LicenseeProof.ts"></script>
<style scoped lang="less" src="./LicenseeProof.less"></style>
