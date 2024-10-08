<!--
    LicenseeList.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div class="licensee-list-container">
        <h1 class="list-title">{{ $t('licensing.licensingListTitle') }}</h1>
        <div class="search-container">
            <button
                class="search-toggle transparent"
                @click="toggleSearch()"
                tabindex="0"
            >
                {{ $t('licensing.searchLabel') }}
            </button>
            <transition name="fade-slow">
                <LicenseeSearch v-show="shouldShowSearch" @searchParams="handleSearch" />
            </transition>
        </div>
        <transition name="fade-slow">
            <ListContainer
                v-show="!shouldShowSearch"
                :listId="listId"
                :listData="this.licenseStore.model"
                :listSize="this.licenseStore.total"
                :sortOptions="sortOptions"
                :sortChange="sortingChange"
                :pageChange="paginationChange"
                :excludeSorting="false"
                :excludeTopPagination="true"
                :excludeBottomPagination="false"
                :isServerPaging="true"
                :pagingPrevKey="$store.state.license.prevLastKey"
                :pagingNextKey="$store.state.license.lastKey"
                :isLoading="$store.state.license.isLoading"
                :loadingError="$store.state.license.error"
            >
                <template v-slot:headers>
                    <LicenseeRow
                        :listId="listId"
                        :item="headerRecord"
                        :isHeaderRow="true"
                        :sortOptions="sortOptions"
                        :sortChange="sortingChange"
                    />
                </template>
                <template v-slot:list>
                    <LicenseeRow
                        v-for="(record, index) in this.licenseStore.model"
                        :key="index"
                        :listId="listId"
                        :item="record"
                    />
                </template>
            </ListContainer>
        </transition>
    </div>
</template>

<script lang="ts" src="./LicenseeList.ts"></script>
<style scoped lang="less" src="./LicenseeList.less"></style>
