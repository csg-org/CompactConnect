<!--
    PrivilegeCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="privilege-card-container">
        <div class="privilege-title-row">
            <div class="privilege-logo-container">
                <img
                    class="privilege-logo"
                    src="@assets/images/black-ellipse.svg"
                    alt="privilege Card Logo"
                />
            </div>
            <span class="privilege-title">
                {{stateContent}}
            </span>
        </div>
        <div class="privilege-info-grid">
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
        <div class="privilege-status">
            {{status}}
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeCard.ts"></script>
<style scoped lang="less" src="./PrivilegeCard.less"></style>
