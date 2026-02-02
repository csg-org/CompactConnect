<!--
    LicenseeRow.vue
    CompactConnect

    Created by InspiringApps on 7/3/2024.
-->

<template>
    <div
        class="licensee-row"
        :class="{ 'is-header': isHeaderRow }"
        @click="!isHeaderRow && navigateToDetail(item.id)"
        @keyup.enter="!isHeaderRow && navigateToDetail(item.id)"
        tabindex="0"
        role="row"
    >
        <div
            class="cell first-name"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('firstName') }"
            @click="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
            @keyup.enter="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('firstName')) ? 0 : -1"
            :role="(isHeaderRow) ? 'columnheader' : 'cell'"
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
            :role="(isHeaderRow) ? 'columnheader' : 'cell'"
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
            class="cell state-of-license"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('stateOfLicense') }"
            @click="isSortOptionEnabled('stateOfLicense') && handleSortSelect('stateOfLicense')"
            @keyup.enter="isSortOptionEnabled('stateOfLicense') && handleSortSelect('stateOfLicense')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('stateOfLicense')) ? 0 : -1"
            :role="(isHeaderRow) ? 'columnheader' : 'cell'"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.homeState') }}:</span>
            {{ item.homeJurisdictionDisplay() }}
            <span v-if="isSortOptionEnabled('stateOfLicense')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('stateOfLicense'),
                'asc': isSortOptionAscending('stateOfLicense'),
                'desc': isSortOptionDescending('stateOfLicense'),
            }"></span>
        </div>
        <div
            class="cell practicing-locations"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('practicingLocations') }"
            @click="isSortOptionEnabled('practicingLocations') && handleSortSelect('practicingLocations')"
            @keyup.enter="isSortOptionEnabled('practicingLocations') && handleSortSelect('practicingLocations')"
            :tabindex="(isHeaderRow && isSortOptionEnabled('practicingLocations')) ? 0 : -1"
            :role="(isHeaderRow) ? 'columnheader' : 'cell'"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.privileges') }}:</span>
            {{ item.privilegeStatesDisplay() }}
            <span v-if="isSortOptionEnabled('practicingLocations')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('practicingLocations'),
                'asc': isSortOptionAscending('practicingLocations'),
                'desc': isSortOptionDescending('practicingLocations'),
            }"></span>
        </div>
    </div>
</template>

<script lang="ts" src="./LicenseeRow.ts"></script>
<style scoped lang="less" src="./LicenseeRow.less"></style>
