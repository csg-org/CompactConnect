<!--
    LicenseeList.vue
    CompactConnect

    Created by InspiringApps on 12/1/2025.
-->

<template>
    <div class="licensee-list-container">
        <transition name="fade-slow" mode="out-in">
            <div v-if="!hasSearched || shouldShowSearchModal" class="search-initial-container">
                <h1 class="list-title">{{ $t('licensing.licensingListTitle') }}</h1>
                <LicenseeSearch
                    :searchParams="searchParams"
                    :isPublicSearch="isPublicSearch"
                    @searchParams="handleSearch"
                />
            </div>
            <div v-else class="licesee-list-container">
                <div class="list-actions-container">
                    <h1 class="list-title no-margin">{{ $t('licensing.licensingListTitle') }}</h1>
                    <div class="search-toggle-container">
                        <button
                            class="search-toggle"
                            @click="toggleSearch()"
                            tabindex="0"
                        >
                            {{ $t('licensing.searchLabel') }}
                        </button>
                        <div v-if="searchDisplayAll" class="search-tag">
                            <span class="title">{{ $t('common.viewing') }}:</span>
                            <span class="search-terms">{{ searchDisplayAll }}</span>
                            <CloseX
                                class="search-terms-reset"
                                @click="resetSearch()"
                                tabindex="0"
                            />
                        </div>
                    </div>
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
                    :isLegacyPaging="false"
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
                            :isPublicSearch="isPublicSearch"
                        />
                    </template>
                </ListContainer>
            </div>
        </transition>
    </div>
</template>

<script lang="ts" src="./LicenseeList.ts"></script>
<style scoped lang="less" src="./LicenseeList.less"></style>
