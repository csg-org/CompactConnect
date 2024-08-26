<!--
    ListContainer.vue
    inHere

    Created by InspiringApps on 5/27/2020.
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
                v-if="hasRecords && !excludeSorting && $matches.tablet.max"
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
                :pagingPrevKey="pagingPrevKey"
                :pagingNextKey="pagingNextKey"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></Pagination>
        </div>
        <ul class="headers">
            <slot name="headers"></slot>
        </ul>
        <div v-if="isLoading" class="list-loading">
            <div class="loading-text">{{ $t('common.loading') }}</div>
            <div class="ellipsis-container">
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
                <div class="ellipsis"></div>
            </div>
        </div>
        <div v-else-if="loadingError" class="loading-error">{{ $t('serverErrors.networkError') }}</div>
        <ul v-else-if="hasRecords" class="list">
            <slot name="list"></slot>
        </ul>
        <div v-else class="no-records">{{ $t('serverErrors.noRecords') }}</div>
        <div class="filter-bar">
            <Pagination
                ariaLabel="Bottom Pagination"
                class="bottom-pagination"
                v-if="hasRecords && !excludeBottomPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pagingPrevKey="pagingPrevKey"
                :pagingNextKey="pagingNextKey"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></Pagination>
        </div>
    </div>
</template>

<script lang="ts" src="./ListContainer.ts"></script>
<style scoped lang="less" src="./ListContainer.less"></style>
