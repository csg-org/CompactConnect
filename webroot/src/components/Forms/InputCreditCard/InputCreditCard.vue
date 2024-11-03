<!--
    InputCreditCard.vue
    CompactConnect

    Created by InspiringApps on 11/1/2024.
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
            inputmode="numeric"
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
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputCreditCard.ts"></script>
<style scoped lang="less" src="./InputCreditCard.less"></style>
