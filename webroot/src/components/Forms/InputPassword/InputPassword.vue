<!--
    InputPassword.vue
    inHere

    Created by InspiringApps on 4/22/2020.
-->

<template>
    <div
        class="input-container input-password"
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
        <div class="password-container">
            <input
                :type="inputType"
                :id="formInput.id"
                :name="formInput.name"
                :placeholder="formInput.placeholder"
                v-model="formInput.value"
                :autocomplete="formInput.autocomplete"
                :aria-label="formInput.label"
                :aria-describedby="`${formInput.id}-error`"
                :aria-errormessage="`${formInput.id}-error`"
                :aria-invalid="!!formInput.errorMessage"
                @blur="blur(formInput)"
                @input="input(formInput)"
                :class="{
                    'has-error': !!formInput.errorMessage,
                    'toggleable-password': showEyeIcon
                }"
            />
            <div
                v-if="showEyeIcon"
                :for="formInput.id"
                class="eye-icon-container"
                @click="togglePassword"
                @keyup.enter="togglePassword"
                role="button"
                :aria-label="$t('common.togglePasswordVisibility')"
                tabindex="0"
            >
                <HidePasswordEye v-if="shouldHidePassword" />
                <ShowPasswordEye v-if="!shouldHidePassword" />
            </div>
        </div>
        <span
            v-if="(!passwordRequirements.length || !showRequirements) && formInput.errorMessage"
            :id="`${formInput.id}-error`"
            class="form-field-error"
            role="alert"
            aria-live="assertive"
        >
            {{ formInput.errorMessage }}
        </span>
        <div
            v-if="showRequirements"
            class="password-requirements"
            :tabindex="(passwordRequirements.length) ? 0 : -1"
        >
            <div
                v-for="{ description, isValid } in passwordRequirements"
                :key="description"
                class="password-requirement"
                :class="{
                    'is-valid': isValid,
                    'is-touched': formInput.isTouched
                }"
            >
                {{ description }}
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./InputPassword.ts"></script>
<style scoped lang="less" src="./InputPassword.less"></style>
