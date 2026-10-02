<!--
    LicenseCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="license-card-container" :class="{ 'active': isActive }">
        <div class="license-heading-row">
            <div class="state-title">
                <div v-if="shouldIncludeLogo" class="license-icon-container">
                    <LicenseHomeIcon v-if="isHomeState && isActive" class="icon-license active" />
                    <LicenseIcon v-else class="icon-license" :class="{ 'active': isActive }" />
                </div>
                {{stateContent}}
            </div>
            <div class="license-status" :class="{ 'active': isActive }">{{statusDisplay}}</div>
            <LicenseActionsModal
                :license="license"
                :licensee="licensee"
            />
        </div>
        <div class="license-heading-row">
            <div class="license-type-abbrev">
                <template v-if="$isAppModeSocialWork">{{ licenseTypeDisplay }}</template>
                <template v-else>{{ licenseTypeAbbrev }}</template>
            </div>
            <div
                v-if="!isPublicSearch"
                class="license-status-description"
                ref="statusDescription"
            >
                {{statusDescriptionDisplay}}
            </div>
        </div>
        <div v-if="$isAppGroupModeMultiState" class="license-scope-container">
            <div v-if="licenseScopeDisplay" class="license-scope" :class="{
                    'single-state': isLicenseScopeSingleState,
                    'multi-state': isLicenseScopeMultiState,
                }">
                <MapPinIcon v-if="isLicenseScopeSingleState" class="scope-icon map-pin-icon" />
                <GlobeIcon v-else-if="isLicenseScopeMultiState" class="scope-icon globe-icon" />
                <span>{{licenseScopeDisplay }}</span>
            </div>
        </div>
        <div class="license-info-grid">
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.licenseNumSymbol')}}</div>
                <div class="info-item rr-block">{{licenseNumber}}</div>
            </div>
            <div v-if="shouldShowDiscipline" class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.disciplineStatus') }}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <template v-if="!isPublicSearch">
            <div v-if="isCompactEligible" class="license-eligibility-container">
                <div class="eligibility-icon-container eligible">
                    <CheckCircleIcon class="eligibility-icon" />
                </div>
                {{ $t('licensing.compactEligible') }}
            </div>
            <div v-else class="license-eligibility-container" :class="{ 'inactive': !isActive }">
                <div class="eligibility-icon-container not-eligible">
                    <CloseXIcon class="eligibility-icon" />
                </div>
                {{ $t('licensing.notCompactEligible') }}
            </div>
        </template>
    </div>
</template>

<script lang="ts" src="./LicenseCard.ts"></script>
<style scoped lang="less" src="./LicenseCard.less"></style>
