<!--
    StyleGuide.vue
    InspiringApps modules

    Created by InspiringApps on 4/28/2021.
-->

<template>
    <div class="style-guide-content">
        <h1>{{ $t('styleGuide.styleGuide') }}</h1>
        <ExampleList listId="pets" />
        <ExampleLanguageSelector />
        <ExampleForm />
        <ExampleModal />
        <ExampleLoadingSpinner />
    </div>
</template>

<script lang="ts" src="./StyleGuide.ts"></script>
<style scoped lang="less" src="./StyleGuide.less"></style>
