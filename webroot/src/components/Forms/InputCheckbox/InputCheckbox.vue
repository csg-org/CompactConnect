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
                @blur="blur(formInput)"
                @change="input(formInput)"
            />
            <span class="checkbox-replacement"></span>
            <label :for="formInput.id" class="input-label">{{ formInput.label }}</label>
        </div>
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputCheckbox.ts"></script>
<style scoped lang="less" src="./InputCheckbox.less"></style>
