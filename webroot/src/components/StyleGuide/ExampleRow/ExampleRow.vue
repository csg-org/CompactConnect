<!--
    ExampleRow.vue
    InspiringApps modules

    Created by InspiringApps on 4/30/2021.
-->

<template>
    <li class="example-row">
        <div class="cell name" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('styleGuide.list.name') }}:</span>
            {{ item.name }}
        </div>
        <div class="cell size" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('styleGuide.list.size') }}:</span>
            {{ item.size }}
        </div>
        <div class="cell disposition" :class="{
            'is-header': isHeaderRow,
            'is-evil': item.isEvil
        }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('styleGuide.list.isEvil') }}:</span>
            {{ item.isEvil }}
        </div>
    </li>
</template>

<script lang="ts" src="./ExampleRow.ts"></script>
<style scoped lang="less" src="./ExampleRow.less"></style>
