<!--
    InputRadioGroup.vue
    InspiringApps modules

    Created by InspiringApps on 5/12/2024.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div
        class="input-container radio-group-container"
        :class="{
            'has-error': !!formInput.errorMessage
        }"
    >
        <div
            v-if="!formInput.shouldHideLabel"
            class="input-label"
        >
            {{ formInput.label }}
            <span v-if="isRequired" class="required-indicator">*</span>
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
                />
                <label
                    :for="`${formInput.name}-${index + 1}`"
                    class="radio-button-label"
                >
                    {{ option.name }}
                </label>
            </div>
        </div>
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputRadioGroup.ts"></script>
<style scoped lang="less" src="./InputRadioGroup.less"></style>
