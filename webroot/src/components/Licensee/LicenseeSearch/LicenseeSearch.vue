<!--
    LicenseeSearch.vue
    CompactConnect

    Created by InspiringApps on 12/1/2025.
-->

<template>
    <div class="licensee-search-container">
        <SearchIcon class="search-icon" />
        <div v-if="isPublicSearch" class="search-title">{{ $t('licensing.searchTitlePublic') }}</div>
        <div v-else class="search-title">{{ $t('licensing.searchTitle') }}</div>
        <div v-if="!isPublicSearch" class="search-subtext">{{ $t('licensing.searchSubtext') }}</div>
        <form @submit.prevent="handleSubmit" class="search-form">
            <div class="search-form-row">
                <MockPopulate
                    :isEnabled="isMockPopulateEnabled"
                    @selected="mockPopulate"
                    class="mock-populate search-input"
                />
            </div>
            <div class="search-form-row">
                <a
                    v-if="isMockPopulateEnabled"
                    @click="resetForm()"
                    @keyup.enter="resetForm()"
                    class="clear-form search-input"
                >{{ $t('common.clear') }}</a>
            </div>
            <div class="search-form-row" v-if="enableCompactSelect">
                <InputSelect
                    :formInput="formData.compact"
                    class="search-input state-select"
                    @input="updateCurrentCompact"
                />
            </div>
            <div class="search-form-row">
                <InputRadioGroup
                    :formInput="formData.searchType"
                    class="search-input search-type-input"
                    @change="updateSearchType"
                />
            </div>
            <div class="search-form-row">
                <InputText
                    :formInput="formData.firstName"
                    class="search-input first-name-input"
                />
            </div>
            <div class="search-form-row">
                <InputText
                    :formInput="formData.lastName"
                    class="search-input last-name-input"
                />
            </div>
            <div class="search-form-row">
                <InputSelect
                    :formInput="formData.homeState"
                    class="search-input home-state-select"
                    :title="(formData.homeState.isDisabled) ? $t('licensing.searchStateDisabled') : ''"
                />
            </div>
            <div class="search-form-row">
                <InputSelect
                    :formInput="formData.privilegeState"
                    class="search-input privilege-state-select"
                />
            </div>
            <div class="search-form-row">
                <div id="privilege-purchase-dates-label" class="date-section-label search-input">
                    {{ $t('licensing.privilegePurchased') }}
                </div>
            </div>
            <div class="search-form-row date-range">
                <InputDate
                    class="search-input date-range-input"
                    :formInput="formData.privilegePurchaseStartDate"
                    :yearRange="[2025, new Date().getFullYear()]"
                    :maxDate="new Date()"
                    :preventMinMaxNavigation="true"
                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                    :startDate="new Date()"
                    aria-labelledby="privilege-purchase-dates-label"
                />
                <span class="date-range-separator">-</span>
                <InputDate
                    class="search-input date-range-input"
                    :formInput="formData.privilegePurchaseEndDate"
                    :yearRange="[2025, new Date().getFullYear()]"
                    :maxDate="new Date()"
                    :preventMinMaxNavigation="true"
                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                    :startDate="new Date()"
                    aria-labelledby="privilege-purchase-dates-label"
                />
            </div>
            <!-- <div class="search-form-row"> @TODO: Adding this in next PR with military status updates
                <InputSelect
                    :formInput="formData.militaryStatus"
                    class="search-input military-status-select"
                />
            </div> -->
            <div class="search-form-row">
                <InputSelect
                    :formInput="formData.investigationStatus"
                    class="search-input investigation-status-select"
                />
            </div>
            <div class="search-form-row">
                <div id="encumber-dates-label" class="date-section-label search-input">
                    {{ $t('licensing.encumbered') }}
                </div>
            </div>
            <div class="search-form-row date-range">
                <InputDate
                    class="search-input date-range-input"
                    :formInput="formData.encumberStartDate"
                    :yearRange="[2025, new Date().getFullYear()]"
                    :maxDate="new Date()"
                    :preventMinMaxNavigation="true"
                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                    :startDate="new Date()"
                    aria-labelledby="encumber-dates-label"
                />
                <span class="date-range-separator">-</span>
                <InputDate
                    class="search-input date-range-input"
                    :formInput="formData.encumberEndDate"
                    :yearRange="[2025, new Date().getFullYear()]"
                    :maxDate="new Date()"
                    :preventMinMaxNavigation="true"
                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                    :startDate="new Date()"
                    aria-labelledby="encumber-dates-label"
                />
            </div>
            <div class="search-form-row">
                <InputText
                    :formInput="formData.npi"
                    class="search-input npi-input"
                />
            </div>
            <div class="search-form-row">
                <InputSubmit
                    v-if="isSearchByProviders"
                    :formInput="formData.submit"
                    :label="$t('common.search')"
                    class="search-input search-submit"
                    :isEnabled="isSearchButtonEnabled"
                />
                <InputSubmit
                    v-else-if="isSearchByPrivileges"
                    :formInput="formData.submit"
                    :label="(licenseStore.isExporting) ? $t('common.exportInProgress') : $t('common.exportCsv')"
                    class="search-input export-submit"
                    :isEnabled="isExportButtonEnabled"
                    :isTransparent="true"
                />
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./LicenseeSearch.ts"></script>
<style scoped lang="less" src="./LicenseeSearch.less"></style>
