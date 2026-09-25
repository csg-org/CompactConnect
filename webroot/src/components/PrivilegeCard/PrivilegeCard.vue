<!--
    PrivilegeCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="privilege-card-container">
        <div class="privilege-title-row" :class="{
            'active': isActive
        }">
            <div class="privilege-title-section">
                <div class="privilege-title">{{stateContent}}</div>
            </div>
            <div class="privilege-status" :class="{ 'active': isActive }">{{statusDisplay}}</div>
            <LicenseActionsModal
                :license="privilege"
                :licensee="licensee"
                type="privilege"
            />
        </div>
        <div class="license-type" :class="{ 'active': isActive }">
            <template v-if="$isAppModeSocialWork">{{privilegeTypeDisplay}}</template>
            <template v-else>{{privilegeTypeAbbrev}}</template>
        </div>
        <div class="privilege-info-grid">
            <div v-if="$isAppGroupModePrivilegePurchase" class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.activeFrom') }}</div>
                <div class="info-item">{{ (isActive) ? activeFromContent : $t('licensing.deactivated') }}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item" :class="{ 'error': isExpired }">{{expiresContent}}</div>
            </div>
            <div v-if="$isAppGroupModePrivilegePurchase" class="info-item-container">
                <div class="info-item-title">{{$t('licensing.privilegeNumSymbol')}}</div>
                <div class="info-item rr-block">{{privilegeId}}</div>
            </div>
            <div v-if="shouldShowDiscipline" class="info-item-container discipline-item">
                <div class="info-item-title">{{ $t('licensing.disciplineStatus') }}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <InputButton
            v-if="$isAppGroupModePrivilegePurchase"
            :label="$t('common.viewDetails')"
            :aria-label="$t('common.viewDetails')"
            class="view-details-button"
            :isTransparent="true"
            @click="goToPrivilegeDetailsPage"
        />
    </div>
</template>

<script lang="ts" src="./PrivilegeCard.ts"></script>
<style scoped lang="less" src="./PrivilegeCard.less"></style>
