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
import LicenseeSearch, { LicenseSearch } from '@components/Licensee/LicenseeSearch/LicenseeSearch.vue';
import LicenseeRow from '@components/Licensee/LicenseeRow/LicenseeRow.vue';
import { SortDirection } from '@store/sorting/sorting.state';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE, PageChangeConfig } from '@store/pagination/pagination.state';
import { PageExhaustError } from '@store/pagination';
import { RequestParamsInterfaceLocal } from '@network/licenseApi/data.api';

@Component({
    name: 'LicenseeList',
    components: {
        ListContainer,
        LicenseeSearch,
        LicenseeRow,
    },
})
class LicenseeList extends Vue {
    @Prop({ required: true }) protected listId!: string;

    //
    // Data
    //
    hasSearched = false;
    shouldShowSearchModal = false;
    isInitialFetchCompleted = false;
    prevKey = '';
    nextKey = '';

    //
    // Lifecycle
    //
    async created() {
        if (this.licenseStore.model?.length) {
            this.hasSearched = true;
        }
    }

    async mounted() {
        if (!this.licenseStore.model?.length) {
            await this.setDefaultSort();
            await this.setDefaultPaging();
        }
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
            // Temp for limited server sorting support
            // { value: 'firstName', name: this.$t('common.firstName') },
            { value: 'lastName', name: this.$t('common.lastName'), isDefault: true },
            // { value: 'ssn', name: this.$t('licensing.ssn') },
            // { value: 'licenseStates', name: this.$t('licensing.homeState') },
            // { value: 'privilegeStates', name: this.$t('licensing.privileges') },
            // { value: 'status', name: this.$t('licensing.status') },
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
    toggleSearch(): void {
        this.shouldShowSearchModal = !this.shouldShowSearchModal;
    }

    handleSearch(params: LicenseSearch): void {
        this.fetchListData(params);

        if (!this.hasSearched) {
            this.hasSearched = true;
        } else {
            this.toggleSearch();
        }
    }

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
        const { prevLastKey } = this.licenseStore;

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

        if (prevLastKey) {
            this.prevKey = prevLastKey;
        }
    }

    async fetchListData(searchParams?: LicenseSearch) {
        const sorting = this.sortingStore.sortingMap[this.listId];
        const { option, direction } = sorting || {};
        const pagination = this.paginationStore.paginationMap[this.listId];
        const { page, size } = pagination || {};
        const requestConfig: RequestParamsInterfaceLocal = {};

        // Sorting params
        if (option) {
            const serverSortByMap = {
                firstName: 'givenName',
                lastName: 'familyName',
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

        // Paging params
        if (page && !this.licenseStore.error) {
            if (this.nextKey && page !== 1) {
                requestConfig.getNextPage = true;
            } else if (this.prevKey) {
                requestConfig.getPrevPage = true;
            }
        }

        // Search params
        requestConfig.compact = this.userStore.currentCompact?.type;

        if (searchParams?.firstName) {
            requestConfig.licenseeFirstName = searchParams.firstName;
        }
        if (searchParams?.lastName) {
            requestConfig.licenseeLastName = searchParams.lastName;
        }
        if (searchParams?.ssn) {
            requestConfig.licenseeSsn = searchParams.ssn;
        }
        if (searchParams?.state) {
            requestConfig.jurisdiction = searchParams.state.toLowerCase();
        }

        // Make fetch request
        await this.$store.dispatch('license/getLicenseesRequest', {
            params: {
                ...requestConfig,
                pageNum: page,
                pageSize: size,
            }
        });

        this.isInitialFetchCompleted = true;

        // If we've reached the end of paging
        if (this.licenseStore.error instanceof PageExhaustError && page > 1) {
            // Support for limited server paging support:
            // The server does not respond with how many total records there are, only keys to fetch
            // the current or next page. So the frontend can't know it's the end of paging until we get back 0 records.
            // At that point, we no longer have usable prevLastKey & lastKey values from the server, and need to re-fetch
            // the last page to get stable.

            // Update pagination store page
            this.$store.dispatch('pagination/updatePaginationPage', {
                paginationId: this.listId,
                newPage: page - 1,
            });
            // Re-fetch with prevLastKey
            await this.$store.dispatch('license/getLicenseesRequest', {
                params: {
                    ...requestConfig,
                    getPrevPage: true,
                    getNextPage: false,
                    pageNum: page,
                    pageSize: size,
                }
            });
            // After fetch, delete lastKey from the store (to disable "next" button)
            this.$store.dispatch('license/setStoreLicenseeLastKey', null);
        }

        return requestConfig;
    }

    async sortingChange() {
        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }

    // Match pageChange() @Prop signature from /components/Lists/Pagination/Pagination.ts
    async paginationChange({ firstIndex, prevNext }: PageChangeConfig) {
        const isInitialInProgress = firstIndex === 0 && prevNext === 0;

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

        if (!isInitialInProgress && this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }
}

export default toNative(LicenseeList);

// export default LicenseeList;
