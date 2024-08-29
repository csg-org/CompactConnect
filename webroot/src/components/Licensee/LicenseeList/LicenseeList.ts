//
//  LicenseeList.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2024.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import LicenseeRow from '@components/Licensee/LicenseeRow/LicenseeRow.vue';
import { SortDirection } from '@store/sorting/sorting.state';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from '@store/pagination/pagination.state';

@Component({
    name: 'LicenseeList',
    components: {
        ListContainer,
        LicenseeRow,
    },
})
class LicenseeList extends Vue {
    @Prop({ required: true }) protected listId!: string;

    //
    // Data
    //
    isInitialFetchCompleted = false;
    prevKey = '';
    nextKey = '';

    //
    // Lifecycle
    //
    async created() {
        await this.setDefaultSort();
        await this.setDefaultPaging();
        await this.fetchListData();
        this.isInitialFetchCompleted = true;
    }

    //
    // Computed
    //
    get sortingStore() {
        return this.$store.state.sorting;
    }

    get paginationStore() {
        return this.$store.state.pagination;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get licenseStore(): any {
        return this.$store.state.license;
    }

    get sortOptions(): Array<any> {
        const options = [
            // Temp for limited server paging support
            // { value: 'firstName', name: this.$t('common.firstName') },
            { value: 'lastName', name: this.$t('common.lastName'), isDefault: true },
            // { value: 'residenceLocation', name: this.$t('licensing.residenceLocation') },
            // { value: 'stateOfLicense', name: this.$t('licensing.stateOfLicense') },
            // { value: 'practicingLocations', name: this.$t('licensing.practicingLocations') },
            { value: 'lastUpdate', name: this.$t('licensing.lastUpdate') },
        ];

        return options;
    }

    get headerRecord() {
        const record = {
            firstName: this.$t('common.firstName'),
            lastName: this.$t('common.lastName'),
            ssnMaskedPartial: () => this.$t('licensing.ssn'),
            licenseStatesDisplay: () => this.$t('licensing.homeState'),
            privilegeStatesDisplay: () => this.$t('licensing.privileges'),
            statusDisplay: () => this.$t('licensing.status'),
        };

        return record;
    }

    //
    // Methods
    //
    async setDefaultSort() {
        const { listId } = this;
        const defaultSortOption = this.sortOptions.find((option) => option.isDefault) || this.sortOptions[0];
        const { option, direction } = this.sortingStore.sortingMap[listId] || {};

        if (!option) {
            await this.$store.dispatch('sorting/updateSortOption', {
                sortingId: listId,
                newOption: defaultSortOption.value,
            });
        }

        if (!direction) {
            await this.$store.dispatch('sorting/updateSortDirection', {
                sortingId: listId,
                newDirection: SortDirection.asc,
            });
        }
    }

    async setDefaultPaging(shouldForce = false) {
        const { listId } = this;
        const { page, size } = this.paginationStore.paginationMap[this.listId] || {};

        if (!page || shouldForce) {
            await this.$store.dispatch('pagination/updatePaginationPage', {
                paginationId: listId,
                newPage: DEFAULT_PAGE,
            });
        }

        if (!size) {
            await this.$store.dispatch('pagination/updatePaginationSize', {
                paginationId: listId,
                newSize: DEFAULT_PAGE_SIZE,
            });
        }
    }

    async fetchListData() {
        const sorting = this.sortingStore.sortingMap[this.listId];
        const { option, direction } = sorting || {};
        const pagination = this.paginationStore.paginationMap[this.listId];
        const { page, size } = pagination || {};
        const requestConfig: any = {};

        if (option) {
            const serverSortByMap = {
                firstName: 'givenName',
                lastName: 'familyName',
                residenceLocation: 'jurisdiction',
                stateOfLicense: 'jurisdiction',
                lastUpdate: 'dateOfUpdate',
            };

            requestConfig.sortBy = serverSortByMap[option];
        }

        if (direction) {
            const serverSortDirectionMap = {
                asc: 'ascending',
                desc: 'descending',
            };

            requestConfig.sortDirection = serverSortDirectionMap[direction];
        }

        // Handle prev / next pages for server paging keys
        if (page && !this.licenseStore.error) {
            if (this.nextKey && page !== 1) {
                requestConfig.getNextPage = true;
            } else if (this.prevKey) {
                requestConfig.getPrevPage = true;
            }
        }

        requestConfig.compact = this.userStore.currentCompact?.type;

        //
        // Temp for limited server filtering support
        //
        requestConfig.jurisdiction = 'al';

        await this.$store.dispatch('license/getLicenseesRequest', {
            params: {
                ...requestConfig,
                pageNum: page,
                pageSize: size,
            }
        });
    }

    async sortingChange() {
        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }

    // Match pageChange() @Prop signature from /components/Lists/Pagination/Pagination.ts
    async paginationChange(firstIdx, lastIdx, prevNext) {
        if (prevNext === -1) {
            this.prevKey = this.licenseStore.prevLastKey;
            this.nextKey = '';
        } else if (prevNext === 1) {
            this.prevKey = '';
            this.nextKey = this.licenseStore.lastKey;
        } else {
            this.prevKey = '';
            this.nextKey = '';
        }

        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }
}

export default toNative(LicenseeList);

// export default LicenseeList;
