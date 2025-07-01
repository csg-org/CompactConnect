<!--
    InputRadioGroup.vue
    InspiringApps modules

    Created by InspiringApps on 5/12/2024.
-->

<template>
    <div
        :id="formInput.id"
        class="input-container radio-group-container"
        :class="{
            'has-error': !!formInput.errorMessage,
            'disabled': formInput.isDisabled,
        }"
    >
        <div
            v-if="!formInput.shouldHideLabel"
            class="input-label"
        >
            <div>
                {{ formInput.label }}
                <span v-if="isRequired && !formInput.isDisabled" class="required-indicator">*</span>
            </div>
            <div
                v-if="formInput.labelSubtext"
                v-html="formInput.labelSubtext"
                class="input-label-subtext"
            >
            </div>
        </div>
        <div
            class="radio-button-group-container"
            :class="{ 'is-horizontal': isGroupHorizontal }"
            role="radiogroup"
            :aria-labelledby="formInput.name"
        >
            <div
                v-for="(option, index) in formInput.valueOptions"
                :key="option.value"
                class="radio-button-container"
            >
                <input
                    type="radio"
                    :id="`${formInput.name}-${index + 1}`"
                    :name="formInput.name"
                    :value="option.value"
                    v-model="formInput.value"
                    :aria-label="option.name"
                    @blur="blur(formInput)"
                    @change="input(formInput)"
                    :disabled="formInput.isDisabled"
                />
                <label
                    :for="`${formInput.name}-${index + 1}`"
                    v-html="option.name"
                    class="radio-button-label"
                    :class="{ 'disabled': formInput.isDisabled }"
                >
                </label>
            </div>
        </div>
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputRadioGroup.ts"></script>
<style scoped lang="less" src="./InputRadioGroup.less"></style>
