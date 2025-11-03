<!--
    InputSelectMultiple.vue
    CompactConnect

    Created by InspiringApps on 10/2/2025.
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
        <div class="multi-select-description">{{ $t('common.selectMultipleKeys') }}</div>
        <select
            multiple="multiple"
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
        <div class="selected-container">
            <div
                v-for="(value, index) in formInput.value"
                :key="index"
                class="selected-value"
            >
                {{ getValueDisplay(value) }}
                <div
                    class="remove"
                    :aria-label="`${$t('common.remove')} ${getValueDisplay(value)}`"
                    role="button"
                    @click="removeSelectedValue(value)"
                    @keyup.enter="removeSelectedValue(value)"
                    tabindex="0"
                >
                    <CloseXIcon />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./InputSelectMultiple.ts"></script>
<style scoped lang="less" src="./InputSelectMultiple.less"></style>
