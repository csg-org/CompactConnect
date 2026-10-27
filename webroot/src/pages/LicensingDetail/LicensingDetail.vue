<!--
    LicensingDetail.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div>
        <transition name="fade">
            <LoadingSpinner v-show="isLoading"></LoadingSpinner>
        </transition>
        <div class="licensee-detail-container">
            <div v-if="isLicenseeUnderInvestigation" class="licensee-alert">
                <AlertTriangleIcon v-if="$matches.tablet.min" class="alert-icon" />
                {{ licenseeInvestigationAlertContent }}
            </div>
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
                    <div v-if="licenseeHomeStateDisplay" class="tag">
                        <div class="tag-icon-container house">
                            <img
                                class="tag-icon"
                                src="@assets/icons/ico-home.svg"
                                :alt="$t('licensing.houseIcon')"
                            />
                        </div>
                        <div class="tag-text">
                            {{ licenseeHomeStateDisplay }}
                        </div>
                    </div>
                    <template v-if="!$isAppModeSocialWork">
                        <div
                            v-for="(license, idx) in activeLicenses"
                            :key="idx"
                            class="tag"
                        >
                            <div class="tag-icon-container">
                                <LicenseIcon />
                            </div>
                            <div class="tag-text">
                                {{ license.issueState.name() }}
                            </div>
                        </div>
                    </template>
                </div>
            </div>
            <div class="personal-information-section rr-block">
                <div class="title-row">
                    <div class="title-info">
                        <div class="pi-logo-container">
                            <img
                                class="home-state-img"
                                src="@assets/icons/ico-personalInfo.svg"
                                :alt="$t('licensing.pInfoIcon')"
                            />
                        </div>
                        <div class="title-text">{{ $t('licensing.personalInformation') }}</div>
                    </div>
                    <CollapseCaretButton
                        @toggleCollapse="togglePersonalInfoCollapsed"
                    />
                </div>
                <div v-if="!isPersonalInfoCollapsed" class="personal-info-container">
                    <div class="vitals-container">
                        <div class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.homeState')}}</div>
                            <div class="info-item">{{homeStateName}}</div>
                        </div>
                        <div class="info-item-container">
                            <div class="info-item-title">{{$t('common.address')}}</div>
                            <div class="info-item">
                                <div class="address-line">
                                    {{addressLine1}}
                                </div>
                                <div v-if="addressLine2" class="address-line">
                                    {{addressLine2}}
                                </div>
                                <div class="address-line">
                                    {{addressLine3}}
                                </div>
                            </div>
                        </div>
                        <div v-if="$isAppGroupModePrivilegePurchase || $isAppModePsyPact" class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.registrationEmail')}}</div>
                            <div class="info-item email">{{registrationEmail}}</div>
                        </div>
                        <div class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.stateEmail')}}</div>
                            <div class="info-item email">{{stateEmail}}</div>
                        </div>
                        <div v-if="$isAppModeSocialWork" class="info-item-container">
                            <div class="info-item-title">{{$t('common.phoneNumber')}}</div>
                            <div class="info-item phone">{{phoneNumber}}</div>
                        </div>
                        <div v-if="dob" class="info-item-container">
                            <div class="info-item-title">{{$t('common.dateOfBirthShort')}}</div>
                            <div class="info-item">{{dob}}</div>
                        </div>
                        <div v-else-if="birthMonthDay" class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.birthMonthDay')}}</div>
                            <div class="info-item">{{birthMonthDay}}</div>
                        </div>
                        <div v-if="licenseeFullSsn" class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.ssn')}}</div>
                            <div class="info-item">{{licenseeFullSsn}}</div>
                        </div>
                        <div v-else-if="ssn" class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.ssn')}}</div>
                            <div class="info-item">{{ssn}}</div>
                            <div
                                v-if="hasLoggedInReadSsnAccessForLicensee && !licenseeFullSsnLoading"
                                class="ssn-reveal-btn"
                                role="button"
                                @click="revealFullSsn"
                                @keyup.enter="revealFullSsn"
                                tabindex="0"
                            >
                                {{ $t('licensing.revealFullSsn') }}
                            </div>
                            <div
                                v-else-if="hasLoggedInReadSsnAccessForLicensee && licenseeFullSsnLoading"
                                class="ssn-reveal-loading"
                            >
                                {{ $t('common.loading') }}
                            </div>
                            <div v-if="licenseeFullSsnError" class="info-item-error">
                                {{ licenseeFullSsnError }}
                            </div>
                        </div>
                    </div>
                    <MilitaryAffiliationInfoBlock v-if="$isAppModeJcc" :licensee="licensee" />
                </div>
            </div>
            <div class="license-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="license-logo-container">
                            <LicenseIcon />
                        </div>
                        <div class="title-text">{{ $t('licensing.licenseDetails') }}</div>
                    </div>
                    <CollapseCaretButton
                        @toggleCollapse="toggleLicensesCollapsed"
                    />
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
                        />
                        <div v-if="isLicenseExpired(license)" class="license-expired-message">
                            {{ $t('licensing.licenseExpired') }}
                        </div>
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
                        <div class="title-text">{{ privilegesTitle }}</div>
                        <ExpirationExplanationIcon v-if="!$isAppModePsyPact" />
                    </div>
                    <CollapseCaretButton @toggleCollapse="togglePrivsCollapsed" />
                </div>
                <div v-if="!isPrivsCollapsed && $isAppModePsyPact" class="privilege-list-container">
                    <PracticeStates :licensee="licensee" />
                </div>
                <div v-else-if="!isPrivsCollapsed" class="privilege-card-list-container">
                    <template v-for="(privilege, index) in licenseePrivileges" :key="index">
                        <div v-if="index > 0
                            && privilege.licenseTypeAbbreviation() !==
                            licenseePrivileges[index - 1].licenseTypeAbbreviation()"
                            class="break-wrap"
                        ></div>
                        <PrivilegeCard
                            :privilege="privilege"
                            :licensee="licensee"
                            class="no-touch-item"
                        />
                    </template>
                </div>
            </div>
            <div v-if="$isAppGroupModeMultiState" class="history-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="history-logo-container">
                            <AlertCircleIcon class="alert-icon" />
                        </div>
                        <div class="title-text">{{ $t('common.history') }}</div>
                    </div>
                    <CollapseCaretButton @toggleCollapse="toggleHistoryCollapsed" />
                </div>
                <div v-if="!isHistoryCollapsed" class="history-list-container">
                    <div v-if="!licenseeHistory.length" class="no-history">
                        {{ $t('licensing.noHistory') }}
                    </div>
                    <div v-else class="history-list">
                        <div v-if="$matches.tablet.min" class="history-row header">
                            <div class="history-cell state">{{ $t('common.state') }}</div>
                            <div class="history-cell event">{{ $t('licensing.event') }}</div>
                            <div class="history-cell date">{{ $t('common.date') }}</div>
                            <div class="history-cell action-type">{{ $t('licensing.encumberAction') }}</div>
                            <div class="history-cell action-basis">{{ $t('licensing.encumberBasisLabel') }}</div>
                        </div>
                        <div v-for="(historyItem, index) in licenseeHistory" :key="index" class="history-row">
                            <div class="history-cell state">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.state') }}:
                                </span>
                                {{ historyItem.state.name() }}
                            </div>
                            <div class="history-cell event">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('licensing.event') }}:
                                </span>
                                {{ historyItem.updateTypeDisplay() }}
                            </div>
                            <div class="history-cell date">
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('common.date') }}:
                                </span>
                                {{ historyItem.effectiveDateDisplay() }}
                            </div>
                            <div
                                v-if="!$matches.phone.only || historyItem.isDisciplineEvent()"
                                class="history-cell action-type"
                            >
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('licensing.encumberAction') }}:
                                </span>
                                {{ historyItem.encumbranceTypeName() }}
                            </div>
                            <div
                                v-if="!$matches.phone.only || historyItem.isDisciplineEvent()"
                                class="history-cell action-basis"
                            >
                                <span v-if="$matches.phone.only" class="cell-title">
                                    {{ $t('licensing.encumberBasisLabel') }}:
                                </span>
                                {{ historyItem.npdbTypeNames().join('; ') || historyItem.noteDisplay() }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicensingDetail.ts"></script>
<style scoped lang="less" src="./LicensingDetail.less"></style>
