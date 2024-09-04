//
//  UserList.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import UserRow from '@components/Users/UserRow/UserRow.vue';
import { SortDirection } from '@store/sorting/sorting.state';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE, PageChangeConfig } from '@store/pagination/pagination.state';
import { PageExhaustError } from '@store/pagination';

@Component({
    name: 'UserList',
    components: {
        ListContainer,
        UserRow,
    }
})
class UserList extends Vue {
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
    async mounted() {
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

    get usersStore(): any {
        return this.$store.state.users;
    }

    get sortOptions(): Array<any> {
        const options = [
            // Temp for limited server paging support
            // { value: 'firstName', name: this.$t('common.firstName') },
            { value: 'lastName', name: this.$t('common.lastName'), isDefault: true },
            // { value: 'permissions', name: this.$t('account.permissions') },
            // { value: 'affiliation', name: this.$t('account.affiliation') },
            // { value: 'states', name: this.$t('account.states') },
            { value: 'accountStatus', name: this.$t('account.accountStatus') },
        ];

        return options;
    }

    get headerRecord() {
        const record = {
            firstName: this.$t('common.firstName'),
            lastName: this.$t('common.lastName'),
            permissionsShortDisplay: () => this.$t('account.permissions'),
            affiliationDisplay: () => this.$t('account.affiliation'),
            statesDisplay: () => this.$t('account.states'),
            accountStatusDisplay: () => this.$t('account.accountStatus'),
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
        const { prevLastKey } = this.usersStore;

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
                permissions: 'permissions',
                affiliation: 'affiliation',
                states: 'jurisdiction',
                accountStatus: 'status',
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
        if (page && !this.usersStore.error) {
            if (this.nextKey && page !== 1) {
                requestConfig.getNextPage = true;
            } else if (this.prevKey) {
                requestConfig.getPrevPage = true;
            }
        }

        requestConfig.compact = this.userStore.currentCompact?.type;

        await this.$store.dispatch('users/getUsersRequest', {
            params: {
                ...requestConfig,
                pageNum: page,
                pageSize: size,
            }
        });

        // If we've reached the end of paging
        if (this.usersStore.error instanceof PageExhaustError && page > 1) {
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
            await this.$store.dispatch('users/getUsersRequest', {
                params: {
                    ...requestConfig,
                    getPrevPage: true,
                    getNextPage: false,
                    pageNum: page,
                    pageSize: size,
                }
            });
            // After fetch, delete lastKey from the store (to disable "next" button)
            this.$store.dispatch('users/setStoreUsersLastKey', null);
        }
    }

    async sortingChange() {
        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }

    // Match pageChange() @Prop signature from /components/Lists/Pagination/Pagination.ts
    async paginationChange({ prevNext }: PageChangeConfig) {
        if (prevNext === -1) {
            this.prevKey = this.usersStore.prevLastKey;
            this.nextKey = '';
        } else if (prevNext === 1) {
            this.prevKey = '';
            this.nextKey = this.usersStore.lastKey;
        } else {
            this.prevKey = '';
            this.nextKey = '';
        }

        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }
}

export default toNative(UserList);

// export default UserList;
