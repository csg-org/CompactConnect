<!--
    LicenseeList.vue
    CompactConnect

    Created by InspiringApps on 7/1/2024.
-->

<template>
    <div class="licensee-list-container">
        <h1 class="list-title">{{ $t('licensing.licensingListTitle') }}</h1>
        <transition name="fade-slow" mode="out-in">
            <div v-if="!hasSearched" class="search-initial-container">
                <LicenseeSearch :searchParams="searchParams" @searchParams="handleSearch" />
            </div>
            <div v-else-if="shouldShowSearchModal" class="search-modal-container">
                <LicenseeSearch :searchParams="searchParams" @searchParams="handleSearch" />
            </div>
            <div v-else class="licesee-list-container">
                <div class="search-toggle-container">
                    <div v-if="hasSearchTerms" class="search-tag">
                        <span class="title">{{ $t('common.viewing') }}:</span>
                        <span class="search-terms">
                            {{ searchDisplayFirstName }}
                            {{ searchDisplayLastName }}
                            {{ searchDisplaySsn }}
                            {{ searchDisplayState }}
                        </span>
                        <CloseX
                            class="search-terms-reset"
                            @click="resetSearch()"
                            tabindex="0"
                        />
                    </div>
                    <button
                        class="search-toggle"
                        @click="toggleSearch()"
                        tabindex="0"
                    >
                        {{ $t('licensing.searchLabel') }}
                    </button>
                </div>
                <ListContainer
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
            </div>
        </transition>
    </div>
</template>

<script lang="ts" src="./LicenseeList.ts"></script>
<style scoped lang="less" src="./LicenseeList.less"></style>
