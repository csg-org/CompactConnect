<!--
    LicensingDetail.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div class="licensee-detail-container">
        <div class="licensee-header">
            <div class="breadcrumbs">
                <router-link class="breadcrumb-link" :to="{ name: 'Licensing', params: { compact } }">
                    {{ $t('licensing.licensingListTitle') }}
                </router-link>
                <span class="breadcrumb-current">/ {{ licenseeNameDisplay }}</span>
            </div>
            <div class="licensee-name">
                <span v-if="licenseStore.isLoading">Loading...</span>
                <span v-else>{{ licenseeNameDisplay }}</span>
            </div>
            <div class="tags">
                <div class="tag">
                    <div class="tag-icon-container">
                        <img
                            class="tag-icon"
                            src="@assets/icons/home-icon.svg"
                            alt="House Icon"
                        />
                    </div>
                    <div class="tag-text">
                        {{ licenseeHomeStateDisplay }}
                    </div>
                </div>
                <div
                    v-for="(license, idx) in licenseeLicenses"
                    :key="idx"
                    class="tag"
                >
                    <div class="tag-icon-container">
                        <img
                            class="tag-icon"
                            src="@assets/icons/home-icon.svg"
                            alt="License Icon"
                        />
                    </div>
                    <div class="tag-text">
                        {{ license.issueState.name() }}
                    </div>
                </div>
            </div>
        </div>
        <div class="personal-information-section">
            <div class="title-row">
                <div class="title-info">
                    <div class="license-logo-container">
                        <img
                            class="home-state-img"
                            src="@assets/images/black-ellipse.svg"
                            alt="Personal Informational List Logo"
                        />
                    </div>
                    <div class="title-text">
                        {{personalInformationTitle}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="togglePersonalInfoCollapsed"
                />
            </div>
            <div v-if="!isPersonalInfoCollapsed" class="personal-info-container">
                <div class="vitals-container">
                    <div class="info-item-container">
                        <div class="info-item-title">{{$t('licensing.homeState')}}</div>
                        <div class="info-item">{{homeState}}</div>
                    </div>
                    <div class="info-item-container">
                        <div class="info-item-title">{{$t('common.address')}}</div>
                        <div class="info-item">{{address}}</div>
                    </div>
                    <div class="info-item-container">
                        <div class="info-item-title">{{$t('licensing.driversLicense')}}</div>
                        <div class="info-item">{{licenseNumber}}</div>
                    </div>
                    <div class="info-item-container">
                        <div class="info-item-title">{{$t('common.dateOfBirthShort')}}</div>
                        <div class="info-item">{{dob}}</div>
                    </div>
                    <div class="info-item-container">
                        <div class="info-item-title">{{$t('licensing.ssn')}}</div>
                        <div class="info-item">{{ssn}}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="license-section">
            <div class="title-row">
                <div class="title-info">
                    <div class="license-logo-container">
                        <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="License List Logo" />
                    </div>
                    <div class="title-text">
                        {{licenseDetails}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="toggleLicensesCollapsed"
                />
            </div>
            <div v-if="!isLicensesCollapsed" class="license-card-list-container">
                <div
                    v-for="(license, index) in licenseList"
                    :key="'license'+index"
                    class="no-touch-item license-chunk"
                >
                    <LicenseCard
                        :license="license"
                    />
                    <div v-if="!checkIfLicenseActive(license)" class="license-expired-message">
                        {{licenseExpiredMessage}}
                    </div>
                </div>
            </div>
        </div>
        <div class="privilege-section">
            <div class="title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                    </div>
                    <div class="title-text">
                        {{recentPrivilegesTitle}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="toggleRecentPrivsCollapsed"
                />
            </div>
            <div v-if="!isRecentPrivsCollapsed" class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in privilegeList"
                    :key="'privilege'+index"
                    :privilege="privilege"
                    class="no-touch-item"
                />
            </div>
        </div>
        <div class="privilege-section">
            <div class="title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img class="home-state-img" src="@assets/images/black-ellipse.svg" alt="Privilege List Logo" />
                    </div>
                    <div class="title-text">
                        {{pastPrivilegesTitle}}
                    </div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="togglePastPrivsCollapsed"
                />
            </div>
            <div v-if="!isPastPrivsCollapsed" class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in privilegeList"
                    :key="'privilege'+index"
                    :privilege="privilege"
                    class="no-touch-item"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicensingDetail.ts"></script>
<style scoped lang="less" src="./LicensingDetail.less"></style>
