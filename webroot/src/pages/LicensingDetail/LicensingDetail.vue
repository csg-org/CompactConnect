<!--
    LicensingDetail.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div class="licensee-detail-container">
        <div class="licensee-header">
            <div class="breadcrumbs">
                <router-link class="breadcrumb-link" :to="{ name: 'Licensing' }">
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
        <div class="licensee-section licenses">
            <div class="licensee-section-title">Licenses</div>
            <div v-if="$matches.tablet.min" class="license-row headers">
                <div class="license-row-cell residence-state header">{{ $t('licensing.residenceLocation') }}</div>
                <div class="license-row-cell license-state header">{{ $t('licensing.stateOfLicense') }}</div>
                <div class="license-row-cell practicing-state header">{{ $t('licensing.practicingLocations') }}</div>
            </div>
            <div
                v-for="(license, idx) in licenseeLicenses"
                :key="idx"
                class="license-row"
            >
                <div class="license-row-cell residence-state">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.residenceLocation') }}: </span>
                    {{ licensee.residenceLocation() }}
                </div>
                <div class="license-row-cell license-state">
                    <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.stateOfLicense') }}: </span>
                    {{ license.issueState.name() }}
                </div>
                <div class="license-row-cell practicing-state">
                    <span v-if="$matches.phone.only" class="cell-title">{{$t('licensing.practicingLocations')}}: </span>
                    {{ licensee.practicingLocationsAll() }}
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
        </div>
        <div class="licensee-section adverse-actions">
            <div class="licensee-section-title">Adverse Actions</div>
            <div class="adverse-action-container">
                <div class="icon"></div>
                <div class="adverse-action">
                    <div class="adverse-action-title">Lorem ipsum dolor</div>
                    <div class="adverse-action-description">
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse tincidunt, magna non
                        vestibulum pulvinar, nunc felis laoreet sem, nec elementum tellus mi quis erat. Cras sit
                        amet tellus lorem. Integer est felis, commodo a molestie id, congue sit amet lorem. Nunc
                        pulvinar lorem id tellus ve.
                    </div>
                </div>
            </div>
            <div class="adverse-action-container">
                <div class="icon"></div>
                <div class="adverse-action">
                    <div class="adverse-action-title">Lorem ipsum dolor</div>
                    <div class="adverse-action-description">
                        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse tincidunt, magna non
                        vestibulum pulvinar, nunc felis laoreet sem, nec elementum tellus mi quis erat. Cras sit
                        amet tellus lorem. Integer est felis, commodo a molestie id, congue sit amet lorem. Nunc
                        pulvinar lorem id tellus ve.
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicensingDetail.ts"></script>
<style scoped lang="less" src="./LicensingDetail.less"></style>
