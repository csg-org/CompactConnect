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
                        <div class="title-text">{{ $t('licensing.recentPrivilegesTitle') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="toggleRecentPrivsCollapsed" />
                </div>
                <div v-if="!isRecentPrivsCollapsed" class="privilege-card-list-container">
                    <PrivilegeCard
                        v-for="(privilege, index) in licenseePrivileges"
                        :key="index"
                        :privilege="privilege"
                        :licensee="licensee"
                        class="no-touch-item"
                    />
                </div>
            </div>
            <div class="privilege-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="title-text">{{ $t('licensing.pastPrivilegesTitle') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="togglePastPrivsCollapsed" />
                </div>
                <div v-if="!isPastPrivsCollapsed" class="privilege-card-list-container">
                    <PrivilegeCard
                        v-for="(privilege, index) in pastPrivilegeList"
                        :key="index"
                        :privilege="privilege"
                        :licensee="licensee"
                        class="no-touch-item"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PublicLicensingDetail.ts"></script>
<style scoped lang="less" src="./PublicLicensingDetail.less"></style>
