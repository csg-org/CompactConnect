<!--
    PublicLicensingDetail.vue
    CompactConnect

    Created by InspiringApps on 3/17/2025.
-->

<template>
    <div>
        <transition name="fade">
            <LoadingSpinner v-show="isLoading"></LoadingSpinner>
        </transition>
        <div class="licensee-detail-container">
            <div class="licensee-header">
                <div class="breadcrumbs">
                    <router-link class="breadcrumb-link" :to="{ name: 'LicneseeSearchPublic' }">
                        {{ $t('licensing.licensingListTitle') }}
                    </router-link>
                    <span class="breadcrumb-current">/ {{ licenseeNameDisplay }}</span>
                </div>
                <div class="licensee-name">
                    <span v-if="licenseStore.isLoading && !licenseeNameDisplay">{{ $t('common.loading') }}</span>
                    <span v-else>{{ licenseeNameDisplay }}</span>
                </div>
                <div v-if="$isAppModeSocialWork" class="licensee-id">
                    {{ $t('licensing.cuid') }}: {{ licenseeCuidDisplay }}
                </div>
                <div class="tags">
                    <div v-if="licenseeHomeStateDisplay" class="tag">
                        <div class="tag-icon-container house">
                            <img
                                class="tag-icon"
                                src="@assets/icons/ico-home.svg"
                                :alt="$t('licensing.houseIcon')"
                            />
                        </div>
                        <div class="tag-text">{{ licenseeHomeStateDisplay }}</div>
                    </div>
                </div>
            </div>
            <div v-if="$isAppGroupModeMultiState" class="license-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="license-logo-container">
                            <LicenseIcon />
                        </div>
                        <div class="title-text">{{ this.$t('licensing.licenseDetails') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="toggleLicensesCollapsed" />
                </div>
                <div v-if="!isLicensesCollapsed" class="license-card-list-container">
                    <div
                        v-for="(license, index) in licenseeLicenses"
                        :key="'license'+index"
                        class="no-touch-item license-chunk"
                    >
                        <LicenseCard
                            :license="license"
                            :licensee="licensee"
                            :homeState="homeState"
                            :isPublicSearch="true"
                        />
                    </div>
                </div>
            </div>
            <div class="privilege-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="privilege-logo-container">
                            <img
                                class="home-state-img"
                                src="@assets/icons/ico-privilege.svg"
                                :alt="$t('licensing.privilegeIcon')"
                            />
                        </div>
                        <div class="title-text">{{ licenseePrivilegesTitle }}</div>
                        <ExpirationExplanationIcon v-if="!$isAppModePsyPact" />
                    </div>
                    <CollapseCaretButton @toggleCollapse="togglePrivsCollapsed" />
                </div>
                <div v-if="!isPrivsCollapsed && $isAppModePsyPact" class="privilege-list-container">
                    <PracticeStates :licensee="licensee" />
                </div>
                <div v-else-if="!isPrivsCollapsed" class="privilege-card-list-container">
                    <PrivilegeCard
                        v-for="(privilege, index) in licenseePrivileges"
                        :key="index"
                        :privilege="privilege"
                        :licensee="licensee"
                        :isPublicSearch="true"
                        class="no-touch-item"
                    />
                </div>
            </div>
            <div v-if="$isAppModeSocialWork" class="history-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="history-logo-container">
                            <AlertCircleIcon class="alert-icon" />
                        </div>
                        <div id="history-title" class="title-text">{{ $t('common.history') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="toggleHistoryCollapsed" />
                </div>
                <div v-if="historyDisclaimer" class="title-description">{{ historyDisclaimer }}</div>
                <div v-if="!isHistoryCollapsed" class="history-list-container">
                    <div v-if="!licenseeHistory.length" class="no-history">
                        {{ $t('licensing.noHistory') }}
                    </div>
                    <div v-else class="history-list" role="table" aria-labelledby="history-title">
                        <div v-if="$matches.tablet.min" class="history-row header" role="row">
                            <div class="history-cell state" role="columnheader">
                                {{ $t('common.state') }}
                            </div>
                            <div class="history-cell event" role="columnheader">
                                {{ $t('licensing.event') }}
                            </div>
                            <div class="history-cell date" role="columnheader">
                                {{ $t('common.date') }}
                            </div>
                        </div>
                        <div
                            v-for="(historyItem, index) in licenseeHistory"
                            :key="index"
                            class="history-row"
                            role="row"
                        >
                            <div class="history-cell state" role="cell">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.state') }}:
                                </span>
                                {{ historyItem.state.name() }}
                            </div>
                            <div class="history-cell event" role="cell">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('licensing.event') }}:
                                </span>
                                {{ historyItem.updateTypeDisplay() }}
                            </div>
                            <div class="history-cell date" role="cell">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.date') }}:
                                </span>
                                {{ historyItem.effectiveDateDisplay() }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PublicLicensingDetail.ts"></script>
<style scoped lang="less" src="./PublicLicensingDetail.less"></style>
