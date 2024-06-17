<!--
    Pagination.vue
    inHere

    Created by InspiringApps on 5/21/2020.
-->

<template>
    <div class="pagination-container" role="navigation" :aria-label="ariaLabel">
        <ul class="pagination-list" v-if="pages && pages.length">
            <li
                @click="isFirstPage ? null : setPage(currentPage - 1)"
                @keyup.enter="isFirstPage ? null : setPage(currentPage - 1)"
                :class="{ clickable: !isFirstPage }"
                class="pagination-item caret"
                :aria-label="$t('paging.previousPage')"
            >
                <LeftCaretIcon :class="{ clickable: !isFirstPage }" />
            </li>
            <li
                v-for="{id, clickable, selected, displayValue} in pages"
                :key="id"
                @click="clickable ? setPage(id) : null"
                @keyup.enter="clickable ? setPage(id) : null"
                class="pagination-item page"
                :class="{ selected, clickable }"
                :aria-label="clickable ? `${$t('paging.goToPage')} ${id}` : $t('paging.notClickable')"
                :aria-current="selected"
                :aria-disabled="!clickable"
            >
                {{ displayValue }}
            </li>
            <li
                @click="isLastPage ? null : setPage(currentPage + 1)"
                @keyup.enter="isLastPage ? null : setPage(currentPage + 1)"
                :class="{ clickable: !isLastPage }"
                class="pagination-item caret"
                :aria-label="$t('paging.nextPage')"
            >
                <RightCaretIcon :class="{ clickable: !isLastPage }" />
            </li>
        </ul>
        <InputSelect
            :formInput="formData.pageSizeOptions"
            @input="setSize"
            class="page-size"
        />
    </div>
</template>

<script lang="ts" src="./Pagination.ts"></script>
<style scoped lang="less" src="./Pagination.less"></style>
