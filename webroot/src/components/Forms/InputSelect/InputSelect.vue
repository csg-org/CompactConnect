<!--
    InputSelect.vue
    inHere

    Created by InspiringApps on 5/28/2020.
-->

<template>
    <div
        class="input-container"
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
        <select
            :id="formInput.id"
            :name="formInput.name"
            v-model="formInput.value"
            :aria-label="formInput.label"
            :aria-describedby="`${formInput.id}-error`"
            :aria-errormessage="`${formInput.id}-error`"
            :aria-invalid="!!formInput.errorMessage"
            :autocomplete="formInput.autocomplete"
            @blur="blur(formInput)"
            @change="input(formInput)"
            class="select-dropdown"
            :class="{
                'has-error': !!formInput.errorMessage
            }"
            :disabled="formInput.isDisabled"
        >
            <option
                v-for="(option, index) in formInput.valueOptions"
                :key="index"
                :value="option.value"
                :disabled="option.isDisabled"
            >
                {{ option.name }}
            </option>
        </select>
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            :id="`${formInput.id}-error`"
            class="form-field-error"
            role="alert"
            aria-live="assertive"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputSelect.ts"></script>
<style scoped lang="less" src="./InputSelect.less"></style>
