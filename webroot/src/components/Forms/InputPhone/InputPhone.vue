<!--
    InputPhone.vue
    inHere

    Created by InspiringApps on 6/19/2020.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div
        class="input-container input-phone-container"
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
        <div class="phone-container">
            <InputSelect
                :formInput="formData.country"
                class="country-select"
                @blur="blurCountry"
                @input="inputCountry"
            />
            <input
                type="text"
                :id="formInput.id"
                :name="formInput.name"
                :placeholder="formInput.placeholder"
                v-model="localValue"
                :value="phoneDisplay"
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

<script lang="ts" src="./InputPhone.ts"></script>
<style scoped lang="less" src="./InputPhone.less"></style>
