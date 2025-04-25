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
        </div>
        <div class="license-heading-row">
            <div class="license-type-abbrev">{{licenseTypeDisplay}}</div>
            <div class="license-status-description" ref="statusDescription">{{statusDescriptionDisplay}}</div>
        </div>
        <div class="license-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{issuedTitle}}</div>
                <div class="info-item">{{issuedContent}}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.licenseNumSymbol')}}</div>
                <div class="info-item">{{licenseNumber}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{disciplineTitle}}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <div v-if="isCompactEligible" class="license-eligibility-container">
            <div class="eligibility-icon-container eligible">
                <CheckCircleIcon class="eligibility-icon" />
            </div>
            {{ $t('licensing.compactEligible') }}
        </div>
        <div v-else class="license-eligibility-container">
            <div class="eligibility-icon-container not-eligible">
                <CloseXIcon class="eligibility-icon" />
            </div>
            {{ $t('licensing.notCompactEligible') }}
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseCard.ts"></script>
<style scoped lang="less" src="./LicenseCard.less"></style>
