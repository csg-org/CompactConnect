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
            >
                {{ option.name }}
            </option>
        </select>
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputSelect.ts"></script>
<style scoped lang="less" src="./InputSelect.less"></style>
