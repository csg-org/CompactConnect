<!--
    InputRange.vue
    <the-app-name>

    Created by InspiringApps on 5/21/2024.
    Copyright © 2024. <the-customer-name>. All rights reserved.
-->

<template>
    <div
        class="input-container input-range-container"
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
        <div
            class="range-container"
            :class="{
                'has-tick-marks': showTickMarks,
                'has-tick-labels': showTickLabels
            }"
        >
            <div class="range-wrapper">
                <input
                    type="range"
                    ref="rangeElement"
                    :id="formInput.id"
                    :name="formInput.name"
                    :min="formInput.rangeConfig.min"
                    :max="formInput.rangeConfig.max"
                    :step="formInput.rangeConfig.stepInterval"
                    v-model.number="formInput.value"
                    :aria-label="formInput.label"
                    @blur="blur(formInput)"
                    @input="input(formInput)"
                    :class="{ 'has-error': !!formInput.errorMessage }"
                />
                <div v-if="showTickMarks" class="tick-markers">
                    <span
                        v-for="step in tickSteps"
                        :key="step"
                        :value="step"
                        class="tick-marker"
                    >
                        {{ showTickLabels ? step : '' }}
                    </span>
                </div>
            </div>
            <span v-if="showValueLabel" class="range-value">{{ formattedValue }}</span>
        </div>
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputRange.ts"></script>
<style scoped lang="less" src="./InputRange.less"></style>
