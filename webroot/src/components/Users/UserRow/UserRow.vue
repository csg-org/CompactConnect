<!--
    UserRow.vue
    CompactConnect

    Created by InspiringApps on 9/4/2024.
-->

<template>
    <li
        class="user-row"
        :class="{ 'is-header': isHeaderRow }"
        @click="!isHeaderRow && navigateToDetail(item.id)"
        @keyup.enter="!isHeaderRow && navigateToDetail(item.id)"
        :tabindex="(isHeaderRow) ? -1 : 0"
    >
        <div
            class="cell first-name"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('firstName') }"
            @click="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
            @keyup.enter="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('firstName')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('common.firstName') }}:</span>
            {{ item.firstName }}
            <span v-if="isSortOptionEnabled('firstName')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('firstName'),
                'asc': isSortOptionAscending('firstName'),
                'desc': isSortOptionDescending('firstName'),
            }"></span>
        </div>
        <div
            class="cell last-name"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('lastName') }"
            @click="isSortOptionEnabled('lastName') && handleSortSelect('lastName')"
            @keyup.enter="isSortOptionEnabled('lastName') && handleSortSelect('lastName')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('lastName')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('common.lastName') }}:</span>
            {{ item.lastName }}
            <span v-if="isSortOptionEnabled('lastName')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('lastName'),
                'asc': isSortOptionAscending('lastName'),
                'desc': isSortOptionDescending('lastName'),
            }"></span>
        </div>
        <div
            class="cell permissions"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('permissions') }"
            @click="isSortOptionEnabled('permissions') && handleSortSelect('permissions')"
            @keyup.enter="isSortOptionEnabled('permissions') && handleSortSelect('permissions')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('permissions')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.permissions') }}:</span>
            {{ item.permissionsShortDisplay(currentCompactType) }}
            <span v-if="isSortOptionEnabled('permissions')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('permissions'),
                'asc': isSortOptionAscending('permissions'),
                'desc': isSortOptionDescending('permissions'),
            }"></span>
        </div>
        <div
            class="cell affiliation"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('affiliation') }"
            @click="isSortOptionEnabled('affiliation') && handleSortSelect('affiliation')"
            @keyup.enter="isSortOptionEnabled('affiliation') && handleSortSelect('affiliation')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('affiliation')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.affiliation') }}:</span>
            {{ item.affiliationDisplay(currentCompactType) }}
            <span v-if="isSortOptionEnabled('affiliation')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('affiliation'),
                'asc': isSortOptionAscending('affiliation'),
                'desc': isSortOptionDescending('affiliation'),
            }"></span>
        </div>
        <div
            class="cell states"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('states') }"
            @click="isSortOptionEnabled('states') && handleSortSelect('states')"
            @keyup.enter="isSortOptionEnabled('states') && handleSortSelect('states')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('states')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.states') }}:</span>
            {{ item.statesDisplay(currentCompactType) }}
            <span v-if="isSortOptionEnabled('states')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('states'),
                'asc': isSortOptionAscending('states'),
                'desc': isSortOptionDescending('states'),
            }"></span>
        </div>
        <div
            class="cell account-status"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('accountStatus') }"
            @click="isSortOptionEnabled('accountStatus') && handleSortSelect('accountStatus')"
            @keyup.enter="isSortOptionEnabled('accountStatus') && handleSortSelect('accountStatus')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('accountStatus')) ? 0 : -1"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.accountStatus') }}:</span>
            {{ item.accountStatusDisplay() }}
            <span v-if="isSortOptionEnabled('accountStatus')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('accountStatus'),
                'asc': isSortOptionAscending('accountStatus'),
                'desc': isSortOptionDescending('accountStatus'),
            }"></span>
        </div>
    </li>
</template>

<script lang="ts" src="./UserRow.ts"></script>
<style scoped lang="less" src="./UserRow.less"></style>
