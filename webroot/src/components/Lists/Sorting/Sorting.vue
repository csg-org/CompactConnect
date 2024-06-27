<!--
    Sorting.vue
    inHere

    Created by InspiringApps on 6/2/2020.
-->

<template>
    <div class="sort-container">
        <div
            class="sort-icon-container"
            @click="toggleSort"
            @keyup.enter="toggleSort"
        >
            <img src="@assets/icons/ico_sort.svg" class="sort-icon" alt="Toggle sort options" />
        </div>
        <div class="sort-toggle" :class="{ 'collapsed': isCollapsed && isPhone}">
            <InputRadioGroup
                :formInput="formData.sortOptions"
                :isGroupHorizontal="true"
                @input="sortOptionChange"
            />
            <span class="group-separator" />
            <InputRadioGroup
                :formInput="formData.sortDirection"
                :isGroupHorizontal="true"
                @input="sortDirectionChange"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./Sorting.ts"></script>
<style scoped lang="less" src="./Sorting.less"></style>
