//
//  Sorting.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Vue,
    Prop
} from 'vue-facing-decorator';

@Component({
    name: 'MixinSorting'
})
class MixinSorting extends Vue {
    @Prop({ required: true }) protected listData!: Array<any>; // Extending class should more specifically type
    @Prop({ required: true }) protected listId!: string;
    @Prop({ required: true }) private sortOptions!: Array<{
        value: string;
        name: string;
        sortingMethod: (a: any, b: any) => number;
    }>;
    @Prop({ default: false }) private excludeSorting?: boolean; // eslint-disable-line lines-between-class-members

    //
    // Data
    //
    selectedSort = ''; // Extending class may override
    isAscending = true;

    //
    // Lifecycle
    //
    created() {
        if (!this.selectedSort && this.sortOptions?.length) {
            this.selectedSort = this.sortOptions[0].value;
        }
    }

    //
    // Computed
    //
    get sortedRecords() {
        const { selectedSort, isAscending, listData } = this;
        let sortedRecordList: any[] = [];

        if (listData && listData.length) {
            sortedRecordList = [...listData];
            const selectedSortOption = this.sortOptions.find((sortOption) =>
                sortOption.value.toLowerCase() === selectedSort.toLowerCase());

            if (selectedSortOption) {
                sortedRecordList.sort((a, b) => selectedSortOption.sortingMethod(a, b));
            }

            if (!isAscending) {
                sortedRecordList.reverse();
            }
        }

        return sortedRecordList;
    }

    //
    // Methods
    //
    sortingChange(sortOption: string, ascending: boolean) {
        this.selectedSort = sortOption;
        this.isAscending = ascending;
    }

    noSort() {
        return 0;
    }
}

// export default toNative(MixinSorting);

export default MixinSorting;
