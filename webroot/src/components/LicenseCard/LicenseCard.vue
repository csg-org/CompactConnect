<!--
    LicenseCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="license-card-container">
        <div class="license-title-row">
            <div class="license-logo-container">
                <img
                    class="license-logo"
                    src="@assets/images/black-ellipse.svg"
                    alt="License Card Logo"
                />
            </div>
            <span class="license-title">
                License
            </span>
        </div>
        <div class="license-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{stateTitle}}</div>
                <div class="info-item">{{stateContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{issuedTitle}}</div>
                <div class="info-item">{{issuedContent}}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{disciplineTitle}}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <div class="license-status">
            {{status}}
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseCard.ts"></script>
<style scoped lang="less" src="./LicenseCard.less"></style>
