<!--
    LicenseCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="license-card-container">
        <div class="license-title-row">
            <div v-if="shouldIncludeLogo" class="license-icon-container">
                <LicenseIcon />
            </div>
            <div class="license-title" :class="{'left-marg': shouldIncludeLogo}">
                {{licenseTitleDisplay}}
            </div>
        </div>
        <div class="license-heading-text">
            <div class="state-title">
                {{stateContent}}
            </div>
            <div class="license-type-abbrev">
                {{licenseTypeDisplay}}
            </div>
        </div>
        <div class="license-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{issuedTitle}}</div>
                <div class="info-item">{{issuedContent}}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item" :class="{ 'error': isExpired }">{{expiresContent}}</div>
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
        <div class="license-status" :class="{'italics': !isActive, 'bold': isActive }">
            {{statusDisplay}}
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseCard.ts"></script>
<style scoped lang="less" src="./LicenseCard.less"></style>
