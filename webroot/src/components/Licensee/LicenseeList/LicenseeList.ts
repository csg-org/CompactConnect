//
//  LicenseeList.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/1/2025.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { serverDateFormat, displayDateFormat } from '@/app.config';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import LicenseeSearch, { LicenseSearch, SearchTypes } from '@components/Licensee/LicenseeSearch/LicenseeSearch.vue';
import LicenseeRow from '@components/Licensee/LicenseeRow/LicenseeRow.vue';
import CloseX from '@components/Icons/CloseX/CloseX.vue';
import { SortDirection } from '@store/sorting/sorting.state';
import { DEFAULT_PAGE, DEFAULT_PAGE_SIZE } from '@store/pagination/pagination.state';
import { SearchParamsInterfaceLocal } from '@network/searchApi/data.api';
import { State } from '@models/State/State.model';
import moment from 'moment';

@Component({
    name: 'LicenseeList',
    components: {
        ListContainer,
        LicenseeSearch,
        LicenseeRow,
        CloseX,
    },
})
class LicenseeList extends Vue {
    @Prop({ required: true }) protected listId!: string;
    @Prop({ default: false }) protected isPublicSearch?: boolean;

    //
    // Data
    //
    hasSearched = false;
    shouldShowSearchModal = false;
    searchErrorOverride = '';
    isInitialFetchCompleted = false;

    //
    // Lifecycle
    //
    async created() {
        if (this.licenseStoreRecordCount) {
            this.hasSearched = true;
        }
    }

    async mounted() {
        if (!this.licenseStoreRecordCount) {
            // License store is empty - apply defaults
            await this.setDefaultSort();
            await this.setDefaultPaging();
        } else if (this.licenseStoreRecordCount === 1 && !this.searchDisplayAll) {
            // Edge case: Returning from a detail page that was refreshed / cache-cleared
            this.shouldShowSearchModal = true;
        } else {
            // License store already has records
            this.isInitialFetchCompleted = true;
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

    get licenseStoreRecordCount(): number {
        return this.licenseStore.model?.length || 0;
    }

    get searchParams(): LicenseSearch {
        return this.licenseStore.search;
    }

    get searchDisplayCompact(): string {
        return (this.isPublicSearch) ? this.userStore.currentCompact?.abbrev() || '' : '';
    }

    get searchDisplayFullName(): string {
        const { firstName = '', lastName = '' } = this.searchParams;

        return `${firstName} ${lastName}`.trim();
    }

    get searchDisplayHomeState(): string {
        const { homeState } = this.searchParams;

        return (homeState) ? `${this.$t('licensing.homeState')}: ${new State({ abbrev: homeState }).name()}` : '';
    }

    get searchDisplayPrivilegeState(): string {
        const { privilegeState } = this.searchParams;

        return (privilegeState) ? `${this.$t('licensing.privilegeState')}: ${new State({ abbrev: privilegeState }).name()}` : '';
    }

    get searchDisplayPrivilegePurchaseDates(): string {
        const { privilegePurchaseStartDate = '', privilegePurchaseEndDate = '' } = this.searchParams;
        let displayDates = '';

        if (privilegePurchaseStartDate || privilegePurchaseEndDate) {
            const startDate = (privilegePurchaseStartDate)
                ? moment(privilegePurchaseStartDate, serverDateFormat).format(displayDateFormat)
                : '∞';
            const endDate = (privilegePurchaseEndDate)
                ? moment(privilegePurchaseEndDate, serverDateFormat).format(displayDateFormat)
                : '∞';

            displayDates = `${this.$t('licensing.purchaseDate')}: ${startDate}-${endDate}`;
        }

        return displayDates;
    }

    get searchDisplayMilitaryStatus(): string {
        const { militaryStatus } = this.searchParams;
        let displayStatus = '';

        if (militaryStatus) {
            const statusOptions = this.$tm('military.militaryStatusOptions') || [];
            const selectedOption = statusOptions.find((statusOption) => statusOption.key === militaryStatus);

            if (selectedOption?.name) {
                displayStatus = `${this.$t('military.militaryStatusTitle')}: ${selectedOption.name}`;
            }
        }

        return displayStatus;
    }

    get searchDisplayInvestigationStatus(): string {
        const { investigationStatus } = this.searchParams;
        let displayStatus = '';

        if (investigationStatus) {
            const statusOptions = this.$tm('licensing.investigationStatusOptions') || [];
            const selectedOption = statusOptions.find((statusOption) => statusOption.key === investigationStatus);

            if (selectedOption?.name) {
                displayStatus = `${selectedOption.name}`;
            }
        }

        return displayStatus;
    }

    get searchDisplayEncumberDates(): string {
        const { encumberStartDate = '', encumberEndDate = '' } = this.searchParams;
        let displayDates = '';

        if (encumberStartDate || encumberEndDate) {
            const startDate = (encumberStartDate)
                ? moment(encumberStartDate, serverDateFormat).format(displayDateFormat)
                : '∞';
            const endDate = (encumberEndDate)
                ? moment(encumberEndDate, serverDateFormat).format(displayDateFormat)
                : '∞';

            displayDates = `${this.$t('licensing.encumbered')}: ${startDate}-${endDate}`;
        }

        return displayDates;
    }

    get searchDisplayNpi(): string {
        const { npi = '' } = this.searchParams;

        return (npi) ? `${this.$t('licensing.npi')}: ${npi}`.trim() : '';
    }

    get searchDisplayAll(): string {
        const joined = [
            this.searchDisplayCompact,
            this.searchDisplayFullName,
            this.searchDisplayHomeState,
            this.searchDisplayPrivilegeState,
            this.searchDisplayPrivilegePurchaseDates,
            this.searchDisplayMilitaryStatus,
            this.searchDisplayInvestigationStatus,
            this.searchDisplayEncumberDates,
            this.searchDisplayNpi
        ].join(', ').trim();

        return joined.replace(/(^[,\s]+)|([,\s]+$)/g, '').replace(/(,\s)\1+/g, ', '); // Replace repeated commas with single comma
    }

    get sortOptions(): Array<any> {
        const options = [
            { value: 'lastName', name: this.$t('common.lastName'), isDefault: true },
        ];

        return options;
    }

    get headerRecord() {
        const record = {
            firstName: this.$t('common.firstName'),
            lastName: this.$t('common.lastName'),
            homeJurisdictionDisplay: () => this.$t('licensing.homeState'),
            privilegeStatesDisplay: () => this.$t('licensing.privileges'),
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
        this.$store.dispatch('license/setStoreSearch', params);
        this.$store.dispatch('pagination/updatePaginationPage', {
            paginationId: this.listId,
            newPage: 1,
        });
        this.searchErrorOverride = '';
        this.fetchListData();

        if (!params.isDirectExport) {
            if (!this.hasSearched) {
                this.hasSearched = true;
            } else {
                this.toggleSearch();
            }
        }
    }

    async resetSearch(): Promise<void> {
        this.$store.dispatch('license/resetStoreSearch');

        if (this.isPublicSearch) {
            await this.$store.dispatch('user/setCurrentCompact', null);
        }

        this.toggleSearch();
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

    async fetchListData(): Promise<SearchParamsInterfaceLocal> {
        const { searchParams } = this;
        const { searchType } = searchParams;
        const requestConfig = this.prepareSearchBody();

        if (searchType === SearchTypes.PROVIDER) {
            // Provider licensee search is a standard REST JSON call
            await this.$store.dispatch('license/getLicenseesSearchRequest', {
                params: { ...requestConfig }
            });
        } else if (searchType === SearchTypes.PRIVILEGE) {
            // Privilege search is a file download call
            requestConfig.isForPrivileges = true;
            await this.handlePrivilegeDownload(requestConfig);
        }

        this.isInitialFetchCompleted = true;

        return requestConfig;
    }

    prepareSearchBody(): SearchParamsInterfaceLocal {
        const { searchParams } = this;
        const sorting = this.sortingStore.sortingMap[this.listId];
        const { option, direction } = sorting || {};
        const pagination = this.paginationStore.paginationMap[this.listId];
        const { page, size } = pagination || {};
        const requestConfig: SearchParamsInterfaceLocal = {};
        const { isDirectExport } = searchParams;

        // Search params
        requestConfig.isPublic = this.isPublicSearch;

        if (searchParams?.compact) {
            requestConfig.compact = searchParams?.compact;
        } else {
            requestConfig.compact = this.userStore.currentCompact?.type;
        }

        if (searchParams?.firstName) {
            requestConfig.licenseeFirstName = searchParams.firstName;
        }
        if (searchParams?.lastName) {
            requestConfig.licenseeLastName = searchParams.lastName;
        }
        if (searchParams?.homeState) {
            requestConfig.homeState = searchParams.homeState.toLowerCase();
        }
        if (searchParams?.privilegeState) {
            requestConfig.privilegeState = searchParams.privilegeState.toLowerCase();
        }
        if (searchParams?.privilegePurchaseStartDate) {
            requestConfig.privilegePurchaseStartDate = searchParams.privilegePurchaseStartDate;
        }
        if (searchParams?.privilegePurchaseEndDate) {
            requestConfig.privilegePurchaseEndDate = searchParams.privilegePurchaseEndDate;
        }
        if (searchParams?.militaryStatus) {
            requestConfig.militaryStatus = searchParams.militaryStatus;
        }
        if (searchParams?.investigationStatus) {
            requestConfig.investigationStatus = searchParams.investigationStatus;
        }
        if (searchParams?.encumberStartDate) {
            requestConfig.encumberStartDate = searchParams.encumberStartDate;
        }
        if (searchParams?.encumberEndDate) {
            requestConfig.encumberEndDate = searchParams.encumberEndDate;
        }
        if (searchParams?.npi) {
            requestConfig.npi = searchParams.npi;
        }

        // Paging params
        if (!isDirectExport) {
            requestConfig.pageNumber = page;
            requestConfig.pageSize = size;
        }

        // Sorting params
        if (!isDirectExport) {
            if (option) {
                const serverSortByMap = {
                    lastName: 'familyName',
                };

                requestConfig.sortBy = serverSortByMap[option];
            }

            if (direction) {
                requestConfig.sortDirection = direction;
            }
        }

        return requestConfig;
    }

    async handlePrivilegeDownload(requestConfig: SearchParamsInterfaceLocal): Promise<void> {
        let errorMessage = '';
        const response = await this.$store.dispatch('license/getPrivilegesRequest', {
            params: { ...requestConfig }
        }).catch((error) => {
            errorMessage = error?.message || error;
        });

        if (errorMessage) {
            this.searchErrorOverride = errorMessage;
        } else if (response) {
            const { fileUrl } = response;
            const tempLink = document.createElement('a');

            if (!fileUrl) {
                this.searchErrorOverride = this.$t('serverErrors.searchErrorGeneral');
            } else {
                tempLink.href = fileUrl;
                tempLink.target = '_blank';
                tempLink.rel = 'noopener noreferrer';
                tempLink.download = `privilege_export.csv`;
                tempLink.click();
            }
        }
    }

    async sortingChange() {
        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }

    async paginationChange() {
        if (this.isInitialFetchCompleted) {
            await this.fetchListData();
        }
    }
}

export default toNative(LicenseeList);

// export default LicenseeList;
