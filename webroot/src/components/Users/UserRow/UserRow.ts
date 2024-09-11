//
//  UserRow.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import {
    Component,
    Vue,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';
import { SortDirection } from '@store/sorting/sorting.state';

@Component({
    name: 'UserRow',
    components: {
        RightCaretIcon,
    },
})
class UserRow extends Vue {
    @Prop({ required: true }) protected listId!: string;
    @Prop({ required: true }) item!: any;
    @Prop({ default: false }) isHeaderRow?: boolean;
    @Prop({ default: []}) sortOptions?: Array<any>;
    @Prop({ default: () => null }) sortChange?: (selectedSortOption?: string, ascending?: boolean) => any;

    //
    // Data
    //
    lastSortSelectOption = '';
    lastSortSelectDirection = '';
    isRowExpanded = false;

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get currentCompactType() {
        return this.userStore.currentCompact?.type;
    }

    get sortingStore() {
        return this.$store.state.sorting;
    }

    get sortingStoreOption(): any {
        return this.sortingStore.sortingMap[this.listId]?.option;
    }

    get sortingStoreDirection(): SortDirection {
        return this.sortingStore.sortingMap[this.listId]?.direction;
    }

    get sortOptionNames(): Array<string> {
        const names: Array<string> = [];

        this.sortOptions?.forEach((option) => {
            if (option.value) {
                names.push(option.value);
            }
        });

        return names;
    }

    get isAccountStatusPending(): boolean {
        return this.item?.accountStatus === 'pending';
    }

    get isAccountStatusEmphasis(): boolean {
        return this.isAccountStatusPending;
    }

    get shouldAllowResendInvite(): boolean {
        return this.isAccountStatusPending;
    }

    //
    // Methods
    //
    isSortOptionEnabled(optionName: string): boolean {
        return Boolean(this.isHeaderRow && this.sortOptionNames.includes(optionName));
    }

    isSortOptionSelected(optionName: string): boolean {
        return Boolean(this.isHeaderRow && this.sortingStoreOption === optionName);
    }

    sortOptionDirection(optionName: string): SortDirection {
        const isOptionSelected = this.isSortOptionSelected(optionName);
        let optionDirection = SortDirection.asc;

        if (isOptionSelected) {
            optionDirection = this.sortingStoreDirection;
        }

        return optionDirection;
    }

    isSortOptionAscending(optionName: string): boolean {
        return Boolean(this.sortOptionDirection(optionName) === SortDirection.asc);
    }

    isSortOptionDescending(optionName: string): boolean {
        return Boolean(this.sortOptionDirection(optionName) === SortDirection.desc);
    }

    async handleSortSelect(optionName: string): Promise<void> {
        await this.handleSortChangeDirection(optionName);
        await this.handleSortChangeOption(optionName);

        if (this.sortChange) {
            this.sortChange(this.sortingStoreOption, this.sortingStoreDirection === SortDirection.asc);
        }
    }

    async handleSortChangeOption(optionName: string, isExternal = false): Promise<void> {
        const sortingId = this.listId;

        if (optionName !== this.sortingStoreOption) {
            if (isExternal) {
                if (this.lastSortSelectOption !== this.sortingStoreOption) {
                    this.lastSortSelectOption = this.sortingStoreOption;
                } else {
                    // Continue
                }
            } else {
                const newOption = optionName;

                this.lastSortSelectOption = optionName;
                await this.$store.dispatch('sorting/updateSortOption', { sortingId, newOption });
            }
        }
    }

    async handleSortChangeDirection(optionName: string, isExternal = false): Promise<void> {
        const sortingId = this.listId;

        if (isExternal) {
            // If the sort direction changed externally, just sync our local state
            if (this.lastSortSelectDirection !== this.sortingStoreDirection) {
                this.lastSortSelectDirection = this.sortingStoreDirection;
            }
        } else if (optionName === this.sortingStoreOption) {
            // If the sort option is remaining the same, just toggle the direction
            const newDirection = (this.sortingStoreDirection === SortDirection.asc)
                ? SortDirection.desc
                : SortDirection.asc;

            await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection });
        } else if (optionName !== this.sortingStoreOption) {
            // If the sort option is changing, default to asc direction
            const newDirection = SortDirection.asc;

            await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection });
        }
    }

    expandRowToggle(): void {
        this.isRowExpanded = !this.isRowExpanded;
    }

    //
    // Watchers
    //
    @Watch('sortingStoreOption') sortStoreOptionUpdate() {
        this.handleSortChangeOption(this.sortingStoreOption, true);
    }

    @Watch('sortingStoreDirection') sortStoreDirectionUpdate() {
        this.handleSortChangeDirection(this.sortingStoreOption, true);
    }
}

export default toNative(UserRow);

// export default UserRow;
