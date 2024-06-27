<!--
    LanguageSelector.vue
    InspiringApps modules

    Created by InspiringApps on 5/8/2024.
-->

<template>
    <div class="language-selector-container">
        <form @submit.prevent="handleSubmit">
            <InputSelect
                v-if="formData.language"
                :formInput="formData.language"
                @input="handleLanguageSelect"
            />
        </form>
    </div>
</template>

<script lang="ts" src="./LanguageSelector.ts"></script>
<style scoped lang="less" src="./LanguageSelector.less"></style>
