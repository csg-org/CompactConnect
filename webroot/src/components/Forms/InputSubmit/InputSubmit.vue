<!--
    InputSubmit.vue
    inHere

    Created by InspiringApps on 4/22/2020.
-->

<template>
    <div class="input-container input-submit-container" :class="{ 'no-margin': formInput.shouldHideMargin }">
        <div v-if="formInput.successMessage || formInput.errorMessage" class="response-message">
            <span
                v-if="formInput.successMessage"
                :id="`${formInput.id}-success`"
                class="success"
                role="status"
                aria-live="polite"
            >
                {{ formInput.successMessage }}
            </span>
            <span
                v-if="formInput.errorMessage"
                :id="`${formInput.id}-error`"
                class="error"
                role="alert"
                aria-live="assertive"
            >
                {{ formInput.errorMessage }}
            </span>
        </div>
        <input
            type="submit"
            :id="formInput.id"
            :name="formInput.name"
            :value="label || formInput.label"
            :disabled="!isEnabled"
            class="input-submit"
            :class="{
                'warning': isWarning,
                'transparent': isTransparent,
                'text-like': isTextLike,
            }"
            :aria-describedby="(formInput.successMessage) ? `${formInput.id}-success` : `${formInput.id}-error`"
            :aria-errormessage="`${formInput.id}-error`"
            :aria-invalid="!!formInput.errorMessage"
        />
    </div>
</template>

<script lang="ts" src="./InputSubmit.ts"></script>
<style scoped lang="less" src="./InputSubmit.less"></style>
