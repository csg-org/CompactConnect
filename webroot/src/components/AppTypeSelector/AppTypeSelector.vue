<!--
    AppTypeSelector.vue
    CompactConnect

    Created by InspiringApps on 9/22/2026.
-->

<template>
    <div class="app-type-selector-container">
        <form @submit.prevent="handleSubmit">
            <InputSelect
                v-if="formData.appType"
                :formInput="formData.appType"
                @input="handleAppTypeSelect"
            />
            <input
                type="submit"
                class="app-type-select-submit"
                tabindex="-1"
                :aria-label="$t('common.submit')"
            />
        </form>
    </div>
</template>

<script lang="ts" src="./AppTypeSelector.ts"></script>
<style scoped lang="less" src="./AppTypeSelector.less"></style>
