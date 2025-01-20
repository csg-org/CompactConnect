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
                    <div
                        v-for="(license, idx) in activeLicenses"
                        :key="idx"
                        class="tag"
                    >
                        <div class="tag-icon-container">
                            <img
                                class="tag-icon"
                                src="@assets/icons/ico-license.svg"
                                :alt="$t('licensing.licenseIcon')"
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
                                :alt="$t('licensing.blackCircle')"
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
                        <div class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.driversLicense')}}</div>
                            <div class="info-item">{{licenseNumber}}</div>
                        </div>
                        <div v-if="dob" class="info-item-container">
                            <div class="info-item-title">{{$t('common.dateOfBirthShort')}}</div>
                            <div class="info-item">{{dob}}</div>
                        </div>
                        <div v-else-if="birthMonthDay" class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.birthMonthDay')}}</div>
                            <div class="info-item">{{birthMonthDay}}</div>
                        </div>
                        <div class="info-item-container">
                            <div class="info-item-title">{{$t('licensing.ssn')}}</div>
                            <div class="info-item">{{ssn}}</div>
                        </div>
                    </div>
                    <div class="core-info-block">
                        <div class="info-row">
                            <div class="chunk">
                                <div class="chunk-title">{{militaryStatusTitleText}}</div>
                                <div class="chunk-text">{{militaryStatus}}</div>
                            </div>
                            <div class="chunk affiliation-type">
                                <div class="chunk-title">{{affiliationTypeTitle}}</div>
                                <div class="chunk-text">{{affiliationType}}</div>
                            </div>
                        </div>
                        <div class="chunk">
                            <div class="chunk-title">{{militaryAffilitionDocs}}</div>
                            <div class="prev-doc-table">
                                <ListContainer
                                    listId="military-affiliations"
                                    :listData="this.affiliations"
                                    :listSize="this.affiliations.length"
                                    :sortOptions="sortOptions"
                                    :sortChange="sortingChange"
                                    :pageChange="paginationChange"
                                    :excludeSorting="true"
                                    :excludeTopPagination="true"
                                    :excludeBottomPagination="true"
                                    :isServerPaging="false"
                                    :emptyListMessage="$t('military.noUploadedDocuments')"
                                    :isLoading="$store.state.user.isLoadingAccount"
                                >
                                    <template v-slot:headers>
                                        <MilitaryDocumentRow
                                            :item="militaryDocumentHeader"
                                            :isHeaderRow="true"
                                        />
                                    </template>
                                    <template v-slot:list>
                                        <MilitaryDocumentRow
                                            v-for="(record, index) in this.affiliations"
                                            :key="index"
                                            :item="record"
                                        />
                                    </template>
                                </ListContainer>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="license-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="license-logo-container">
                            <img
                                class="home-state-img"
                                src="@assets/images/black-ellipse.svg"
                                :alt="$t('licensing.blackCircle')"
                            />
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
                        v-for="(license, index) in licenseeLicenses"
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
                            <img
                                class="home-state-img"
                                src="@assets/images/black-ellipse.svg"
                                :alt="$t('licensing.blackCircle')"
                            />
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
                        v-for="(privilege, index) in licenseePrivileges"
                        :key="index"
                        :privilege="privilege"
                        class="no-touch-item"
                    />
                </div>
            </div>
            <div class="privilege-section">
                <div class="title-row">
                    <div class="title-info">
                        <div class="privilege-logo-container">
                            <img
                                class="home-state-img"
                                src="@assets/images/black-ellipse.svg"
                                :alt="$t('licensing.blackCircle')"
                            />
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
                        v-for="(privilege, index) in pastPrivilegeList"
                        :key="index"
                        :privilege="privilege"
                        class="no-touch-item"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicensingDetail.ts"></script>
<style scoped lang="less" src="./LicensingDetail.less"></style>
