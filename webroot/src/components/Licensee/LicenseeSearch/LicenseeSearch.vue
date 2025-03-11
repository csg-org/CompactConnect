<!--
    LicenseeSearch.vue
    CompactConnect

    Created by InspiringApps on 9/12/2024.
-->

<template>
    <div class="licensee-search-container">
        <SearchIcon class="search-icon" />
        <div class="search-title">{{ $t('licensing.searchTitle') }}</div>
        <div class="search-subtext">{{ $t('licensing.searchSubtext') }}</div>
        <form @submit.prevent="handleSubmit" class="search-form">
            <div class="search-form-row">
                <InputText
                    :formInput="formData.firstName"
                    class="search-input first-name-input"
                    @input="customValidateLastName(false)"
                />
                <InputText
                    :formInput="formData.lastName"
                    class="search-input last-name-input"
                    @input="customValidateLastName(true)"
                    @blur="customValidateLastName(true)"
                />
            </div>
            <div class="search-form-row">
                <InputSelect :formInput="formData.state" class="search-input state-select" />
            </div>
            <div class="search-form-row">
                <InputSubmit
                    :formInput="formData.submit"
                    :label="$t('licensing.searchLabel')"
                    class="search-input search-submit"
                />
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./LicenseeSearch.ts"></script>
<style scoped lang="less" src="./LicenseeSearch.less"></style>
