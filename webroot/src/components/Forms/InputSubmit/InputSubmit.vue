<!--
    InputSubmit.vue
    inHere

    Created by InspiringApps on 4/22/2020.
-->

<template>
    <div class="input-container input-submit-container" :class="{ 'no-margin': formInput.shouldHideMargin }">
        <div v-if="formInput.successMessage || formInput.errorMessage" class="response-message">
            <span v-if="formInput.successMessage" class="success">{{ formInput.successMessage }}</span>
            <span v-if="formInput.errorMessage" class="error">{{ formInput.errorMessage }}</span>
        </div>
        <input
            type="submit"
            :id="formInput.id"
            :name="formInput.name"
            :value="label || formInput.label"
            :disabled="!isEnabled"
            class="input-submit"
        />
    </div>
</template>

<script lang="ts" src="./InputSubmit.ts"></script>
<style scoped lang="less" src="./InputSubmit.less"></style>
