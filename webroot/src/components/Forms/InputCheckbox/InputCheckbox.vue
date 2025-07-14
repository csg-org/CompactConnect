<!--
    InputCheckbox.vue
    inHere

    Created by InspiringApps on 1/22/2021.
-->

<template>
    <div class="input-container checkbox-container">
        <div class="checkbox-wrapper">
            <input
                type="checkbox"
                :id="formInput.id"
                :name="formInput.name"
                v-model="formInput.value"
                :disabled="formInput.isDisabled"
                :aria-label="formInput.label"
                :aria-describedby="`${formInput.id}-error`"
                :aria-errormessage="`${formInput.id}-error`"
                :aria-invalid="!!formInput.errorMessage"
                @blur="blur(formInput)"
                @change="input"
            />
            <span class="checkbox-replacement"></span>
            <label v-html="formInput.label" :for="formInput.id" class="input-label"></label>
        </div>
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

<script lang="ts" src="./InputCheckbox.ts"></script>
<style scoped lang="less" src="./InputCheckbox.less"></style>
