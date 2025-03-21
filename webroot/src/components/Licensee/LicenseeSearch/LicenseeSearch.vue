<!--
    LicenseeSearch.vue
    CompactConnect

    Created by InspiringApps on 9/12/2024.
-->

<template>
    <div class="licensee-search-container">
        <SearchIcon class="search-icon" />
        <div v-if="isPublicSearch" class="search-title">{{ $t('licensing.searchTitlePublic') }}</div>
        <div v-else class="search-title">{{ $t('licensing.searchTitle') }}</div>
        <div v-if="!isPublicSearch" class="search-subtext">{{ $t('licensing.searchSubtext') }}</div>
        <form @submit.prevent="handleSubmit" class="search-form">
            <div class="search-form-row" v-if="enableCompactSelect">
                <InputSelect
                    :formInput="formData.compact"
                    class="search-input state-select"
                    @input="updateCurrentCompact"
                />
            </div>
            <div class="search-form-row">
                <InputSelect
                    :formInput="formData.state"
                    class="search-input state-select"
                    :title="(formData.state.isDisabled) ? $t('licensing.searchStateDisabled') : ''"
                />
            </div>
            <div class="search-form-row">
                <InputText
                    :formInput="formData.firstName"
                    class="search-input first-name-input"
                    @input="customValidateLastName(false)"
                />
            </div>
            <div class="search-form-row">
                <InputText
                    :formInput="formData.lastName"
                    class="search-input last-name-input"
                    @input="customValidateLastName(true)"
                    @blur="customValidateLastName(true)"
                />
            </div>
            <div class="search-form-row">
                <InputSubmit
                    :formInput="formData.submit"
                    :label="$t('common.search')"
                    class="search-input search-submit"
                />
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./LicenseeSearch.ts"></script>
<style scoped lang="less" src="./LicenseeSearch.less"></style>
