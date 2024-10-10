<!--
    InputSearch.vue
    CompactConnect

    Created by InspiringApps on 9/11/2024.
-->

<template>
    <div
        class="input-container input-search"
        :class="{
            'form-row': formInput.isFormRow,
            'no-margin': formInput.shouldHideMargin,
            'has-error': !!formInput.errorMessage
        }"
    >
        <label
            v-if="!formInput.shouldHideLabel"
            :for="formInput.id"
        >
            {{ formInput.label }}
            <span v-if="isRequired" class="required-indicator">*</span>
        </label>
        <div class="input-wrapper">
            <SearchIcon class="search-icon" />
            <input
                type="text"
                :id="formInput.id"
                :name="formInput.name"
                :placeholder="formInput.placeholder"
                v-model="formInput.value"
                :autocomplete="formInput.autocomplete"
                :aria-label="formInput.label"
                @blur="blur(formInput)"
                @input="input(formInput)"
                :class="{ 'has-error': !!formInput.errorMessage }"
            />
        </div>
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputSearch.ts"></script>
<style scoped lang="less" src="./InputSearch.less"></style>
