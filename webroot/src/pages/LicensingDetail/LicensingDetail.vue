<!--
    LicensingDetail.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div class="licensee-detail-container">
        <div class="licensee-header">
            <div class="breadcrumbs">
                <router-link class="breadcrumb-link" :to="{ name: 'Licensing', params: { compact } }">
                    {{ $t('licensing.licensingListTitle') }}
                </router-link>
                <span class="breadcrumb-current">/ {{ licenseeNameDisplay }}</span>
            </div>
            <div class="licensee-name">
                <span v-if="licenseStore.isLoading">Loading...</span>
                <span v-else>{{ licenseeNameDisplay }}</span>
            </div>
            <div class="license-tags">
                <div
                    v-for="(license, idx) in licenseeLicenses"
                    :key="idx"
                    class="license-tag"
                >
                    {{ license.issueState.name() }}
                </div>
            </div>
        </div>
        <div class="license-section">
            <div class="license-section-title-row">
                <div class="license-logo-container">
                    <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="License List Logo" />
                </div>
                <div class="license-title">
                    {{licenseDetails}}
                </div>
            </div>
            <div class="license-card-list-container">
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
        </div>
        <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="privilege-logo-container">
                    <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                </div>
                <div class="privilege-title">
                    {{recentPrivilegesTitle}}
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
        <!-- <div class="licensee-section licenses">
            <div class="licensee-section-title">Licenses</div>
            <div v-if="$matches.tablet.min" class="license-row headers">
                <div class="license-row-cell residence-location header">{{ $t('licensing.residenceLocation') }}</div>
                <div class="license-row-cell home-state header">{{ $t('licensing.homeState') }}</div>
                <div class="license-row-cell privilege-states header">{{ $t('licensing.privileges') }}</div>
            </div>
            <div class="license-row">
                <div class="license-row-cell residence-location">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.residenceLocation') }}: </span>
                </div>
                <div class="license-row-cell home-state">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.homeState') }}: </span>
                    {{ licenseeHomeStateDisplay }}
                </div>
                <div class="license-row-cell privilege-states">
                    <span v-if="$matches.phone.only" class="cell-title">{{$t('licensing.privileges')}}: </span>
                    {{ licenseePrivilegeStatesDisplay }}
                </div>
            </div>
        </div>
        <div class="licensee-section details">
            <div class="licensee-section-title">Details</div>
            <div v-if="$matches.tablet.min" class="license-row headers">
                <div class="license-row-cell issue-date header">{{ $t('licensing.issueDate') }}</div>
                <div class="license-row-cell expire-date header">{{ $t('licensing.expireDate') }}</div>
            </div>
            <div
                v-for="(license, idx) in licenseeLicenses"
                :key="idx"
                class="license-row"
            >
                <div class="license-row-cell issue-date">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.issueDate') }}: </span>
                    {{ license.issueDateDisplay() }}
                </div>
                <div class="license-row-cell expire-date">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.expireDate') }}: </span>
                    {{ license.expireDateDisplay() }}
                </div>
            </div>
        </div> -->
    </div>
</template>

<script lang="ts" src="./LicensingDetail.ts"></script>
<style scoped lang="less" src="./LicensingDetail.less"></style>
