<!--
    InputText.vue
    inHere

    Created by InspiringApps on 6/15/2020.
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
        <input
            type="text"
            :id="formInput.id"
            :name="formInput.name"
            :placeholder="formInput.placeholder"
            v-model="formInput.value"
            ref="input"
            :autocomplete="formInput.autocomplete"
            :aria-label="formInput.label"
            @blur="blur(formInput)"
            @input="input(formInput)"
            :class="{ 'has-error': !!formInput.errorMessage }"
        />
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputText.ts"></script>
<style scoped lang="less" src="./InputText.less"></style>
