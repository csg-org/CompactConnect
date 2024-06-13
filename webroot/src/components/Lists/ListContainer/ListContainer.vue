<!--
    ListContainer.vue
    inHere

    Created by InspiringApps on 5/27/2020.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div class="list-container">
        <div class="filter-bar">
            <CompactToggle
                v-if="hasRecords && includeCompactToggle"
                :compactId="listId"
                :isCompact="isCompact"
                v-on="$listeners"
            />
            <Sorting
                v-if="hasRecords && !excludeSorting"
                :listId="listId"
                :sortOptions="sortOptions"
                :sortChange="sortChange"
                :sortingId="listId"
            />
            <Pagination
                ariaLabel="Top Pagination"
                v-if="hasRecords && !excludeTopPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></Pagination>
        </div>
        <ul class="headers">
            <slot name="headers"></slot>
        </ul>
        <div v-if="isLoading" class="list-loading">
            <div class="loading-text">Loading</div>
            <div class="ellipsis-container">
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
            </div>
        </div>
        <ul v-else-if="hasRecords" class="list">
            <slot name="list"></slot>
        </ul>
        <div v-else class="no-records">No records to display</div>
        <div class="filter-bar">
            <Pagination
                ariaLabel="Bottom Pagination"
                class="bottom-pagination"
                v-if="hasRecords && !excludeBottomPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig">
            /></Pagination>
        </div>
    </div>
</template>

<script lang="ts" src="./ListContainer.ts"></script>
<style scoped lang="less" src="./ListContainer.less"></style>
