<!--
    CompactSelector.vue
    CompactConnect

    Created by InspiringApps on 10/2/2024.
-->

<template>
    <div v-if="shouldDisplay" class="compact-selector-container">
        <form @submit.prevent="handleSubmit">
            <InputSelect
                v-if="formData.compact"
                :formInput="formData.compact"
                @input="handleCompactSelect"
            />
            <input
                type="submit"
                class="compact-select-submit"
                tabindex="-1"
                :aria-label="$t('common.submit')"
            />
        </form>
    </div>
</template>

<script lang="ts" src="./CompactSelector.ts"></script>
<style scoped lang="less" src="./CompactSelector.less"></style>
