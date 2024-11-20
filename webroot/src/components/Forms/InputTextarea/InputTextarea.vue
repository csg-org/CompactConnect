<!--
    InputTextarea.vue
    inHere

    Created by InspiringApps on 7/21/2020.
-->

<template>
    <div
        class="input-container input-textarea"
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
        <textarea
            :id="formInput.id"
            :name="formInput.name"
            :placeholder="formInput.placeholder"
            v-model="formInput.value"
            :autocomplete="formInput.autocomplete"
            :aria-label="formInput.label"
            @blur="blur(formInput)"
            @input="input(formInput)"
            :class="{
                'has-error': !!formInput.errorMessage,
                'resize-x': shouldResizeX,
                'resize-y': shouldResizeY,
                'resize-all': shouldResize,
                'border-color-match-bg': shouldBorderMatchBgColor
            }"
        />
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
        <span
            v-if="formInput.showMax"
            class="remaining-count"
        >
            {{ $t('inputErrors.remainingCharacters') }}: {{ remainingCharacters }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputTextarea.ts"></script>
<style scoped lang="less" src="./InputTextarea.less"></style>
