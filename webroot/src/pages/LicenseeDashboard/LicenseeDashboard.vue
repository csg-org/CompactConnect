<!--
    LicenseeDashboard.vue
    CompactConnect

    Created by InspiringApps on 9/23/2024.
-->

<template>
    <div class="licensee-dashboard-container">
        <div class="top-block">
            <div class="welcome-user">{{ $t('common.welcome') }}, {{ userFullName }}</div>
            <div class="button-block">
                <div class="btn-container">
                    <InputButton
                        :label="$t('licensing.generateVerification')"
                        :aria-label="$t('licensing.generateVerification')"
                        :isTransparent="true"
                        class="btn view-military-btn"
                        :isEnabled="isGenerateProofEnabled"
                        @click="viewLicenseeProof"
                    />
                    <div class="btn-subtext">{{ $t('licensing.generateVerificationSubtext') }}</div>
                </div>
                <div class="btn-container">
                    <InputButton
                        :label="`+ ${this.$t('licensing.obtainPrivileges')}`"
                        :aria-label="$t('licensing.obtainPrivileges')"
                        class="btn obtain-priv-btn"
                        :isEnabled="isPrivilegePurchaseEnabled"
                        @click="startPrivPurchaseFlow"
                    />
                </div>
            </div>
        </div>
        <div class="license-section">
            <HomeStateBlock
                v-if="homeJurisdiction"
                :state="homeJurisdiction"
                class="no-touch-item"
            />
            <div
                v-for="(license, index) in licenseeLicenses"
                :key="'license'+index"
                class="no-touch-item license-chunk"
            >
                <LicenseCard
                    :license="license"
                    :licensee="licensee"
                    :homeState="homeJurisdiction"
                    :shouldIncludeLogo="true"
                />
            </div>
        </div>
        <div class="privilege-section">
            <div class="privilege-section-title-row">
                <div class="title-info">
                    <div class="privilege-logo-container">
                        <img
                            class="home-state-img"
                            src="@assets/icons/ico-privilege.svg"
                            :alt="$t('licensing.privilegeIcon')"
                        />
                    </div>
                    <div class="title-text">{{ $t('licensing.privileges') }}</div>
                </div>
                <CollapseCaretButton
                    @toggleCollapse="togglePrivsCollapsed"
                />
            </div>
            <div v-if="!isPrivsCollapsed" class="privilege-card-list-container">
                <PrivilegeCard
                    v-for="(privilege, index) in licenseePrivileges"
                    :key="index"
                    :privilege="privilege"
                    :licensee="licensee"
                    class="no-touch-item"
                />
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeDashboard.ts"></script>
<style scoped lang="less" src="./LicenseeDashboard.less"></style>
