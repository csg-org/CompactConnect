<!--
    ExampleList.vue
    InspiringApps modules

    Created by InspiringApps on 4/30/2021.
-->

<template>
    <Section class="example-list-section">
        <h2>{{ $t('styleGuide.exampleList') }}</h2>
        <div class="example-list-container">
            <ListContainer
                :listId="listId"
                :listData="this.styleguideStore.model"
                :listSize="this.styleguideStore.total"
                :sortOptions="sortOptions"
                :sortChange="sortingChange"
                :pageChange="paginationChange"
                :excludeSorting="false"
                :excludeTopPagination="true"
                :excludeBottomPagination="false"
                :isServerPaging="true"
                :isLoading="$store.state.styleguide.isLoading"
            >
                <template v-slot:headers>
                    <ExampleRow
                        :item="headerRecord"
                        :isHeaderRow="true"
                    />
                </template>
                <template v-slot:list>
                    <ExampleRow
                        v-for="(record, index) in this.styleguideStore.model"
                        :key="index"
                        :item="record"
                    />
                </template>
            </ListContainer>
        </div>
    </Section>
</template>

<script lang="ts" src="./ExampleList.ts"></script>
<style scoped lang="less" src="./ExampleList.less"></style>
