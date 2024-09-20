<!--
    Pagination.vue
    inHere

    Created by InspiringApps on 5/21/2020.
-->

<template>
    <div class="pagination-container" role="navigation" :aria-label="ariaLabel">
        <ul class="pagination-list" v-if="pages && pages.length">
            <li
                v-for="{id, clickable, selected, displayValue} in pages"
                :key="id"
                @click="clickable ? setPage(id) : null"
                @keyup.enter="clickable ? setPage(id) : null"
                :tabindex="(clickable) ? 0 : -1"
                class="pagination-item page"
                :class="{ selected, clickable }"
                :aria-label="clickable ? `${$t('paging.goToPage')} ${id}` : $t('paging.notClickable')"
                :aria-current="selected"
                :aria-disabled="!clickable"
            >
                {{ displayValue }}
            </li>
            <li
                v-if="pagingNextKey"
                @click="setPage(currentPage + 1, 1)"
                @keyup.enter="setPage(currentPage + 1, 1)"
                tabindex="0"
                class="pagination-item caret clickable next"
                :aria-label="$t('paging.nextPage')"
            >
                <span>{{ $t('paging.nextPage') }} <RightCaretIcon /></span>
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
