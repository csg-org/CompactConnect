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
            <div v-if="isAppGroupModeMultiState" class="license-section">
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
                        <div class="title-text">{{ $t('licensing.privileges') }}</div>
                        <ExpirationExplanationIcon />
                    </div>
                    <CollapseCaretButton @toggleCollapse="togglePrivsCollapsed" />
                </div>
                <div v-if="!isPrivsCollapsed" class="privilege-card-list-container">
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
            <div v-if="isAppModeSocialWork" class="discipline-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="discipline-logo-container">
                            <AlertCircleIcon class="alert-icon" />
                        </div>
                        <div class="title-text">{{ $t('licensing.disciplineTitle') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="toggleDisciplineCollapsed" />
                </div>
                <div v-if="disciplineDisclaimer" class="title-description">{{ disciplineDisclaimer }}</div>
                <div v-if="!isDisciplineCollapsed" class="discipline-list-container">
                    <div v-if="!licenseeDiscipline.length" class="no-discipline">
                        {{ $t('licensing.noDiscipline') }}
                    </div>
                    <div v-else class="discipline-list">
                        <div v-if="$matches.tablet.min" class="discipline-row header">
                            <div class="discipline-cell state">{{ $t('common.state') }}</div>
                            <div class="discipline-cell start-date">{{ $t('common.startDate') }}</div>
                            <div class="discipline-cell end-date">{{ $t('common.endDate') }}</div>
                        </div>
                        <div v-for="(discipline, index) in licenseeDiscipline" :key="index" class="discipline-row">
                            <div class="discipline-cell state">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.state') }}:
                                </span>
                                {{ discipline.state.name() }}
                            </div>
                            <div class="discipline-cell start-date">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.startDate') }}:
                                </span>
                                {{ discipline.startDateDisplay() }}
                            </div>
                            <div class="discipline-cell end-date">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.endDate') }}:
                                </span>
                                {{ discipline.endDateDisplay() }}
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
