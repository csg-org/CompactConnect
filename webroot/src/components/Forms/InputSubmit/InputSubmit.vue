<!--
    InputSubmit.vue
    inHere

    Created by InspiringApps on 4/22/2020.
-->

<template>
    <div class="input-container input-submit-container" :class="{ 'no-margin': formInput.shouldHideMargin }">
        <span
            v-if="formInput.successMessage && !formInput.shouldHideErrorMessage"
            :id="`${formInput.id}-success`"
            class="success"
            role="status"
            aria-live="polite"
        >
            {{ formInput.successMessage }}
        </span>
        <span
            v-else-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            :id="`${formInput.id}-error`"
            class="error"
            role="alert"
            aria-live="assertive"
        >
            {{ formInput.errorMessage }}
        </span>
        <input
            type="submit"
            :id="formInput.id"
            :name="formInput.name"
            :value="label || formInput.label"
            :disabled="!isEnabled"
            class="input-submit"
            :class="{
                'warning': isWarning,
            }"
            :aria-describedby="(formInput.successMessage) ? `${formInput.id}-success` : `${formInput.id}-error`"
            :aria-errormessage="`${formInput.id}-error`"
            :aria-invalid="!!formInput.errorMessage"
        />
    </div>
</template>

<script lang="ts" src="./InputSubmit.ts"></script>
<style scoped lang="less" src="./InputSubmit.less"></style>
