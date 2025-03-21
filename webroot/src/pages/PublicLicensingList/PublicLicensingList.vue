<!--
    PublicLicensingList.vue
    CompactConnect

    Created by InspiringApps on 3/5/2025.
-->

<template>
    <Section class="licensing-list-section">
        <LicenseeList listId="licensees-public" :isPublicSearch="true" />
    </Section>
</template>

<script lang="ts" src="./PublicLicensingList.ts"></script>
<style scoped lang="less" src="./PublicLicensingList.less"></style>
