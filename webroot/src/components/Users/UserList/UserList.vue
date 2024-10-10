<!--
    UserList.vue
    CompactConnect

    Created by InspiringApps on 9/4/2024.
-->

<template>
    <div class="user-list-container">
        <h1 class="list-title">{{ $t('account.usersListTitle') }}</h1>
        <div class="list-actions-container">
            <div class="search-container">
                <form @submit.prevent="handleSearch">
                    <InputSearch :formInput="formData.userSearch" class="user-search" />
                    <input
                        type="submit"
                        class="user-search-submit"
                        tabindex="-1"
                        :aria-label="$t('common.submit')"
                    />
                </form>
            </div>
        </div>
        <ListContainer
            :listId="listId"
            :listData="this.usersStore.model"
            :listSize="this.usersStore.total"
            :sortOptions="sortOptions"
            :sortChange="sortingChange"
            :pageChange="paginationChange"
            :excludeSorting="false"
            :excludeTopPagination="true"
            :excludeBottomPagination="false"
            :isServerPaging="true"
            :pagingPrevKey="$store.state.users.prevLastKey"
            :pagingNextKey="$store.state.users.lastKey"
            :isLoading="$store.state.users.isLoading"
            :loadingError="$store.state.users.error"
            :emptyListMessage="emptyMessage"
        >
            <template v-slot:headers>
                <UserRow
                    :listId="listId"
                    :item="headerRecord"
                    :isHeaderRow="true"
                    :sortOptions="sortOptions"
                    :sortChange="sortingChange"
                />
            </template>
            <template v-slot:list>
                <UserRow
                    v-for="(record, index) in this.usersStore.model"
                    :key="index"
                    :listId="listId"
                    :item="record"
                />
            </template>
        </ListContainer>
    </div>
</template>

<script lang="ts" src="./UserList.ts"></script>
<style scoped lang="less" src="./UserList.less"></style>
