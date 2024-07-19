<!--
    LicenseeRow.vue
    CompactConnect

    Created by InspiringApps on 7/3/2024.
-->

<template>
    <li class="licensee-row" :class="{ 'is-header': isHeaderRow }">
        <div
            class="cell first-name"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('firstName') }"
            @click="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
            @keyup.enter="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
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
            class="cell residence-location"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('residenceLocation') }"
            @click="isSortOptionEnabled('residenceLocation') && handleSortSelect('residenceLocation')"
            @keyup.enter="isSortOptionEnabled('residenceLocation') && handleSortSelect('residenceLocation')"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.residenceLocation') }}:</span>
            {{ item.residenceLocation() }}
            <span v-if="isSortOptionEnabled('residenceLocation')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('residenceLocation'),
                'asc': isSortOptionAscending('residenceLocation'),
                'desc': isSortOptionDescending('residenceLocation'),
            }"></span>
        </div>
        <div
            class="cell state-of-license"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('stateOfLicense') }"
            @click="isSortOptionEnabled('stateOfLicense') && handleSortSelect('stateOfLicense')"
            @keyup.enter="isSortOptionEnabled('stateOfLicense') && handleSortSelect('stateOfLicense')"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.stateOfLicense') }}:</span>
            {{ item.licenseStatesDisplay() }}
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
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.practicingLocations') }}:</span>
            {{ item.practicingLocationsDisplay() }}
            <span v-if="isSortOptionEnabled('practicingLocations')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('practicingLocations'),
                'asc': isSortOptionAscending('practicingLocations'),
                'desc': isSortOptionDescending('practicingLocations'),
            }"></span>
        </div>
        <div
            class="cell last-updated"
            :class="{ 'is-sort-enabled': isSortOptionEnabled('lastUpdate') }"
            @click="isSortOptionEnabled('lastUpdate') && handleSortSelect('lastUpdate')"
            @keyup.enter="isSortOptionEnabled('lastUpdate') && handleSortSelect('lastUpdate')"
        >
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('licensing.lastUpdate') }}:</span>
            {{ item.lastUpdatedDisplay() }}
            <span v-if="isSortOptionEnabled('lastUpdate')" class="sort-icon" :class="{
                'is-selected': isSortOptionSelected('lastUpdate'),
                'asc': isSortOptionAscending('lastUpdate'),
                'desc': isSortOptionDescending('lastUpdate'),
            }"></span>
        </div>
    </li>
</template>

<script lang="ts" src="./LicenseeRow.ts"></script>
<style scoped lang="less" src="./LicenseeRow.less"></style>
