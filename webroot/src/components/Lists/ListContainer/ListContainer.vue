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
            <PaginationLegacy
                ariaLabel="Top Pagination"
                v-if="isLegacyPaging && hasRecords && !excludeTopPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pagingPrevKey="pagingPrevKey"
                :pagingNextKey="pagingNextKey"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></PaginationLegacy>
            <Pagination
                ariaLabel="Top Pagination"
                v-else-if="!isLegacyPaging && hasRecords && !excludeTopPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></Pagination>
        </div>
        <div class="table-container" role="table">
            <slot name="headers" v-if="$matches.tablet.min"></slot>
            <div v-if="isLoading" class="list-loading" role="row" tabindex="0">
                <div class="loading-text" role="cell">{{ $t('common.loading') }}</div>
                <div class="ellipsis-container" role="cell" aria-label="loading-spinner">
                    <div class="ellipsis"></div>
                    <div class="ellipsis"></div>
                    <div class="ellipsis"></div>
                    <div class="ellipsis"></div>
                </div>
            </div>
            <div v-else-if="loadingError" class="loading-error" role="row" tabindex="0">
                <span role="cell">{{ loadingErrorDisplay }}</span>
            </div>
            <template v-else-if="hasRecords">
                <slot name="list"></slot>
            </template>
            <div v-else class="no-records" role="row" tabindex="0"><span role="cell">{{ emptyMessage }}</span></div>
        </div>
        <div class="filter-bar">
            <PaginationLegacy
                ariaLabel="Bottom Pagination"
                class="bottom-pagination"
                v-if="isLegacyPaging && hasRecords && !excludeBottomPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pagingPrevKey="pagingPrevKey"
                :pagingNextKey="pagingNextKey"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></PaginationLegacy>
            <Pagination
                ariaLabel="Bottom Pagination"
                class="bottom-pagination"
                v-else-if="!isLegacyPaging && hasRecords && !excludeBottomPagination"
                :paginationId="listId"
                :listSize="listTotalSize"
                :pageChange="pageChange"
                :pageSizeConfig="pageSizeConfig"
            ></Pagination>
        </div>
    </div>
</template>

<script lang="ts" src="./ListContainer.ts"></script>
<style scoped lang="less" src="./ListContainer.less"></style>
