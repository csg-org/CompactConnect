<!--
    MilitaryDocumentRow.vue
    InspiringApps modules

    Created by InspiringApps on 4/30/2021.
-->

<template>
    <li class="example-row">
        <div class="cell name" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('styleGuide.list.isEvil') }}:</span>
            {{ item.name }}
        </div>
        <div class="cell size" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('styleGuide.list.isEvil') }}:</span>
            {{ item.date }}
        </div>
    </li>
</template>

<script lang="ts" src="./MilitaryDocumentRow.ts"></script>
<style scoped lang="less" src="./MilitaryDocumentRow.less"></style>
