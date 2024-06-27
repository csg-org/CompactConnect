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
            >
                <HidePasswordEye v-if="shouldHidePassword" />
                <ShowPasswordEye v-if="!shouldHidePassword" />
            </div>
        </div>
        <!-- <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span> -->
        <div class="password-requirements">
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
